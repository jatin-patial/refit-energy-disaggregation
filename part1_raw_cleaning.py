
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

raw_file = Path("data/REFIT_RAW_081116/RAW_House1_Part1.csv")
clean_file = Path("data/cleaned/house1_combined_1min.csv")
plot_folder = Path("data/cleaned/plots")
plot_folder.mkdir(parents=True, exist_ok=True)

# Choose the first 24 hours of Part 1
raw = pd.read_csv(raw_file, parse_dates=["Time"])
start = raw["Time"].min().floor("D")
end = start + pd.Timedelta(days=1)

raw = raw[(raw["Time"] >= start) & (raw["Time"] < end)]
raw = raw.set_index("Time")

cols = ["Aggregate", "Appliance1", "Appliance2"]
raw_min = raw[cols].resample("1min").mean()

clean = pd.read_csv(clean_file, parse_dates=["Time"], index_col="Time")
clean = clean.loc[(clean.index >= start) & (clean.index < end)]

for col in cols:
    plt.figure(figsize=(12, 4))
    plt.plot(raw_min.index, raw_min[col], label="Raw, 1-minute mean")
    plt.plot(clean.index, clean[col], label="Combined cleaned data")
    plt.title(f"{col}: Before and After Cleaning")
    plt.xlabel("Time")
    plt.ylabel("Power (W)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(plot_folder / f"{col}_comparison.png", dpi=150)
    plt.close()

print("Plots saved to:", plot_folder)
print("Created plots for:", ", ".join(cols))
