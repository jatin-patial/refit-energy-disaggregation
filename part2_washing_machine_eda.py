from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

DATA_DIR = Path("data/CLEAN_REFIT_081116")
OUT_DIR = Path("results/part2")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Official metadata mapping: household -> washing-machine column
HOUSES = {
    2: "Appliance2",
    5: "Appliance3",
    6: "Appliance2",
    10: "Appliance5",
}

# Explicit cycle rule: active when washer power is >10 W.
# A cycle must contain at least 5 active minutes.
ACTIVE_THRESHOLD_W = 10
MIN_CYCLE_MINUTES = 5
MAX_GAP_MINUTES = 1


def load_house(house, washer_col):
    path = DATA_DIR / f"CLEAN_House{house}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Could not find {path}")

    df = pd.read_csv(path, low_memory=False)
    df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
    df = df.dropna(subset=["Time"]).sort_values("Time")
    df = df.drop_duplicates(subset="Time", keep="first")

    for col in ["Aggregate", washer_col]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # One-minute means. Keep missing minutes as NaN; do not fill long outages.
    minute = (
        df.set_index("Time")[["Aggregate", washer_col]]
        .resample("1min")
        .mean()
    )
    minute = minute.rename(columns={washer_col: "Washer"})
    return minute



def detect_cycles(minute):
    active = minute["Washer"].gt(ACTIVE_THRESHOLD_W).fillna(False)
    active = active & minute["Washer"].notna()

    # Do not bridge missing-data intervals.
    groups = []
    current = []
    inactive_gap = 0

    for timestamp, is_active in active.items():
        if is_active:
            if current and inactive_gap > MAX_GAP_MINUTES:
                groups.append(current)
                current = []
            current.append(timestamp)
            inactive_gap = 0
        elif current:
            inactive_gap += 1
            if inactive_gap > MAX_GAP_MINUTES:
                groups.append(current)
                current = []
                inactive_gap = 0

    if current:
        groups.append(current)

    rows = []

    for timestamps in groups:
        start, end = timestamps[0], timestamps[-1]
        segment = minute.loc[start:end, "Washer"]
        active_minutes = int((segment > ACTIVE_THRESHOLD_W).sum())

        if active_minutes >= MIN_CYCLE_MINUTES and len(segment) <= 120:
            rows.append({
                "start": start,
                "end": end,
                "duration_minutes": len(segment),
                "active_minutes": active_minutes,
                "mean_power_W": segment.mean(),
                "peak_power_W": segment.max(),
                "energy_Wh_approx": segment.sum() / 60,
            })

    return pd.DataFrame(rows, columns=[
        "start", "end", "duration_minutes", "active_minutes",
        "mean_power_W", "peak_power_W", "energy_Wh_approx"
    ])



def main():
    summaries = []
    all_cycles = []
    loaded = {}

    for house, washer_col in HOUSES.items():
        minute = load_house(house, washer_col)
        
        # Weekday vs weekend usage
        valid_data = minute.dropna(subset=["Washer"]).copy()
        valid_data["day_type"] = (
            valid_data.index.dayofweek >= 5
        ).astype(int)
        valid_data["day_type"] = valid_data["day_type"].map({
            0: "Weekday",
            1: "Weekend"
        })

        day_usage = valid_data.groupby("day_type").agg(
            mean_power_W=("Washer", "mean"),
            active_minutes=("Washer", lambda x: (x > ACTIVE_THRESHOLD_W).sum()),
            recorded_minutes=("Washer", "count")
        )

        day_usage.to_csv(
            OUT_DIR / f"house{house}_weekday_weekend.csv"
        )
        print(f"\nHouse {house}: weekday vs weekend")
        print(day_usage)

        loaded[house] = minute
        cycles = detect_cycles(minute)
        if not cycles.empty:
            print(f"\nHouse {house} cycle duration percentiles (minutes):")
            print(cycles["duration_minutes"].quantile([0.25, 0.5, 0.75, 0.90, 0.95, 0.99]))
            print("Cycles longer than 2 hours:", (cycles["duration_minutes"] > 120).sum())

        # Coverage and missing-data statistics
        washer = minute["Washer"]
        valid = washer.notna()
        active_minutes = int((washer[valid] > ACTIVE_THRESHOLD_W).sum())
        zero_minutes = int((washer[valid] <= ACTIVE_THRESHOLD_W).sum())

        summaries.append({
            "house": house,
            "washer_column": washer_col,
            "start": minute.index.min(),
            "end": minute.index.max(),
            "minutes": len(minute),
            "washer_missing_minutes": int(washer.isna().sum()),
            "washer_missing_percent": round(washer.isna().mean() * 100, 2),
            "valid_minutes": int(valid.sum()),
            "active_minutes_gt_10W": active_minutes,
            "zero_or_inactive_minutes_le_10W": zero_minutes,
            "cycle_count": len(cycles),
            "median_cycle_duration_min": (
                round(cycles["duration_minutes"].median(), 2)
                if not cycles.empty else None
            ),
            "median_cycle_peak_W": (
                round(cycles["peak_power_W"].median(), 2)
                if not cycles.empty else None
            ),
        })

        if not cycles.empty:
            cycles.insert(0, "house", house)
            all_cycles.append(cycles)

        # Plot first 24 hours with available data
        valid_times = minute.index[minute["Aggregate"].notna()]
        if len(valid_times):
            start = valid_times[0]
            window = minute.loc[start:start + pd.Timedelta(hours=24)]
            fig, ax1 = plt.subplots(figsize=(12, 5))
            ax1.plot(window.index, window["Aggregate"], label="Aggregate", linewidth=1)
            ax1.set_ylabel("Aggregate power (W)")
            ax1.set_xlabel("Time")
            ax2 = ax1.twinx()
            ax2.plot(window.index, window["Washer"], label="Washing machine",
                     linewidth=1, alpha=0.85)
            ax2.set_ylabel("Washing-machine power (W)")
            ax1.set_title(f"House {house}: first 24 hours (1-minute means)")
            ax1.grid(True, alpha=0.25)
            fig.tight_layout()
            fig.savefig(OUT_DIR / f"house{house}_first24h.png", dpi=150)
            plt.close(fig)

        # Plot a detected cycle with the highest peak power, if any
        if not cycles.empty:
            best = cycles.loc[cycles["peak_power_W"].idxmax()]
            cycle_window = minute.loc[
                best["start"] - pd.Timedelta(minutes=10):
                best["end"] + pd.Timedelta(minutes=10)
            ]
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(cycle_window.index, cycle_window["Washer"], linewidth=1.2)
            ax.axhline(ACTIVE_THRESHOLD_W, linestyle="--",
                       label=f"Active threshold ({ACTIVE_THRESHOLD_W} W)")
            ax.set_title(f"House {house}: example washing-machine cycle")
            ax.set_xlabel("Time")
            ax.set_ylabel("Washing-machine power (W)")
            ax.grid(True, alpha=0.25)
            ax.legend()
            fig.tight_layout()
            fig.savefig(OUT_DIR / f"house{house}_example_cycle.png", dpi=150)
            plt.close(fig)

        # Hour-of-day usage profile
        hourly = minute["Washer"].groupby(minute.index.hour).mean()
        fig, ax = plt.subplots(figsize=(8, 4))
        hourly.reindex(range(24)).plot(kind="bar", ax=ax)
        ax.set_title(f"House {house}: mean washing-machine power by hour")
        ax.set_xlabel("Hour of day")
        ax.set_ylabel("Mean power (W)")
        fig.tight_layout()
        fig.savefig(OUT_DIR / f"house{house}_hourly_profile.png", dpi=150)
        plt.close(fig)

    summary_df = pd.DataFrame(summaries)
    summary_df.to_csv(OUT_DIR / "household_summary.csv", index=False)

    if all_cycles:
        pd.concat(all_cycles, ignore_index=True).to_csv(
            OUT_DIR / "washing_machine_cycles.csv", index=False
        )
    else:
        pd.DataFrame(columns=[
            "house", "start", "end", "duration_minutes", "mean_power_W",
            "peak_power_W", "energy_Wh_approx"
        ]).to_csv(OUT_DIR / "washing_machine_cycles.csv", index=False)

    # Cross-house comparison of mean washer power by hour
    fig, ax = plt.subplots(figsize=(10, 5))
    for house, minute in loaded.items():
        minute["Washer"].groupby(minute.index.hour).mean().reindex(range(24)).plot(
            ax=ax, label=f"House {house}"
        )
    ax.set_title("Washing-machine mean power by hour: household comparison")
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("Mean power (W)")
    ax.legend()
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "cross_house_hourly_comparison.png", dpi=150)
    plt.close(fig)

    print("\nHOUSEHOLD SUMMARY")
    print(summary_df.to_string(index=False))
    print(f"\nResults saved to: {OUT_DIR.resolve()}")
    print("Cycle rule: >10 W, at least 5 active minutes; inactive gaps up to 3 minutes are merged.")
    print("Note: this simple rule does not merge brief inactive gaps within a cycle.")


if __name__ == "__main__":
    main()
