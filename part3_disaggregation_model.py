from pathlib import Path
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

DATA_DIR = Path("data/CLEAN_REFIT_081116")
OUT_DIR = Path("results/part3")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Verified against the REFIT metadata workbook.
HOUSES = {
    2: "Appliance2",
    5: "Appliance3",
    6: "Appliance2",
    10: "Appliance5",
}
TRAIN_FRACTION = 0.80
MAX_TRAIN_ROWS = 100_000
RANDOM_STATE = 42


def load_minute_data(house, washer_col):
    path = DATA_DIR / f"CLEAN_House{house}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing dataset file: {path}")

    df = pd.read_csv(path, usecols=["Time", "Aggregate", washer_col], low_memory=False)
    df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
    df["Aggregate"] = pd.to_numeric(df["Aggregate"], errors="coerce")
    df[washer_col] = pd.to_numeric(df[washer_col], errors="coerce")
    df = df.dropna(subset=["Time"]).sort_values("Time")
    df = df.drop_duplicates(subset="Time", keep="first")
    df = df.set_index("Time")

    minute = df.resample("1min").mean()
    minute = minute.rename(columns={washer_col: "Washer"})
    return minute[["Aggregate", "Washer"]]


def make_features(minute):
    x = pd.DataFrame(index=minute.index)
    aggregate = minute["Aggregate"]

    x["aggregate"] = aggregate
    for lag in [1, 2, 5, 10, 15, 30, 60]:
        x[f"aggregate_lag_{lag}"] = aggregate.shift(lag)

    for window in [5, 15, 30, 60]:
        x[f"aggregate_mean_{window}"] = aggregate.shift(1).rolling(window).mean()
        x[f"aggregate_max_{window}"] = aggregate.shift(1).rolling(window).max()

    minute_of_day = minute.index.hour * 60 + minute.index.minute
    day_of_week = minute.index.day_of_week
    x["hour_sin"] = np.sin(2 * np.pi * minute_of_day / 1440)
    x["hour_cos"] = np.cos(2 * np.pi * minute_of_day / 1440)
    x["dow_sin"] = np.sin(2 * np.pi * day_of_week / 7)
    x["dow_cos"] = np.cos(2 * np.pi * day_of_week / 7)
    return x


def regression_metrics(y_true, y_pred):
    return {
        "MAE_W": mean_absolute_error(y_true, y_pred),
        "RMSE_W": np.sqrt(mean_squared_error(y_true, y_pred)),
        "R2": r2_score(y_true, y_pred) if len(y_true) > 1 else np.nan,
    }


def main():
    metrics_rows = []

    for house, washer_col in HOUSES.items():
        print(f"\nProcessing House {house} ({washer_col})...")
        minute = load_minute_data(house, washer_col)
        features = make_features(minute)
        data = features.copy()
        data["target"] = minute["Washer"]
        data = data.replace([np.inf, -np.inf], np.nan).dropna()

        if len(data) < 1000:
            warnings.warn(f"House {house} has too few usable rows: {len(data)}")
            continue

        split = int(len(data) * TRAIN_FRACTION)
        train = data.iloc[:split]
        test = data.iloc[split:]

        # Keep model fitting bounded for large household files.
        if len(train) > MAX_TRAIN_ROWS:
            train = train.sample(
                n=MAX_TRAIN_ROWS, random_state=RANDOM_STATE
            ).sort_index()

        X_train = train.drop(columns="target")
        y_train = train["target"]
        X_test = test.drop(columns="target")
        y_test = test["target"]

        # Zero-load baseline.
        baseline_pred = np.zeros(len(y_test), dtype=float)
        baseline = regression_metrics(y_test, baseline_pred)


        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=18,
            min_samples_leaf=3,
            max_features=0.8,
            n_jobs=-1,
            random_state=RANDOM_STATE,
        )
        model.fit(X_train, y_train)
        pred = np.clip(model.predict(X_test), 0, None)
        
        
        active_mask = y_test > 10

        if active_mask.any():
            active_actual = y_test[active_mask]
            active_pred = pred[active_mask]
            active_zero = np.zeros(len(active_actual))

            print(f"  Active minutes: {len(active_actual):,}")
            print(f"  Active zero-baseline MAE: {mean_absolute_error(active_actual, active_zero):.2f} W")
            print(f"  Active model MAE: {mean_absolute_error(active_actual, active_pred):.2f} W")
            print(f"  Active zero-baseline RMSE: {np.sqrt(mean_squared_error(active_actual, active_zero)):.2f} W")
            print(f"  Active model RMSE: {np.sqrt(mean_squared_error(active_actual, active_pred)):.2f} W")


        learned = regression_metrics(y_test, pred)

        metrics_rows.append({
            "house": house,
            "washer_column": washer_col,
            "train_rows_used": len(train),
            "test_rows": len(test),
            "baseline_MAE_W": baseline["MAE_W"],
            "baseline_RMSE_W": baseline["RMSE_W"],
            "baseline_R2": baseline["R2"],
            "model_MAE_W": learned["MAE_W"],
            "model_RMSE_W": learned["RMSE_W"],
            "model_R2": learned["R2"],
        })

        # Plot a 7-day slice of the test period for readability.
        plot_count = min(len(test), 7 * 24 * 60)
        plot_index = test.index[:plot_count]
        plot_actual = y_test.iloc[:plot_count]
        plot_pred = pd.Series(pred, index=test.index).iloc[:plot_count]

        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(plot_index, plot_actual, label="Actual washer power", linewidth=1)
        ax.plot(plot_index, plot_pred, label="Predicted washer power", linewidth=1)
        ax.set_title(f"House {house}: actual vs predicted washing-machine power")
        ax.set_xlabel("Time")
        ax.set_ylabel("Power (W)")
        ax.grid(True, alpha=0.25)
        ax.legend()
        fig.tight_layout()
        fig.savefig(OUT_DIR / f"house{house}_actual_vs_predicted.png", dpi=150)
        plt.close(fig)

        # Save actual and predicted values for further inspection.
        pd.DataFrame({
            "Time": test.index,
            "actual_washer_W": y_test.to_numpy(),
            "predicted_washer_W": pred,
        }).to_csv(OUT_DIR / f"house{house}_predictions.csv", index=False)

        print(f"  Usable rows: {len(data):,}; train: {len(train):,}; test: {len(test):,}")
        print(f"  Zero baseline MAE: {baseline['MAE_W']:.2f} W | RMSE: {baseline['RMSE_W']:.2f} W")
        print(f"  Random Forest MAE: {learned['MAE_W']:.2f} W | RMSE: {learned['RMSE_W']:.2f} W | R2: {learned['R2']:.3f}")

    results = pd.DataFrame(metrics_rows)
    results.to_csv(OUT_DIR / "model_metrics.csv", index=False)

    print("\nMODEL METRICS")
    if results.empty:
        print("No results produced. Check the data files and column mappings.")
    else:
        print(results.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print(f"\nSaved results to: {OUT_DIR.resolve()}")
    print("Split: chronological 80% train / 20% test separately within each household.")
    print("Caution: this evaluates future-period performance for known households, not transfer to an unseen household.")


if __name__ == "__main__":
    main()
