# REFIT Washing-Machine Load Analysis

A Python project for cleaning raw REFIT data, exploring washing-machine electricity usage across households, and estimating washing-machine power from aggregate household power.

## Project Parts

### Part 1 — Raw-data cleaning

Script: `part1_raw_cleaning.py`

- Inspects timestamp order, duplicate timestamps, missing intervals, and extreme readings.
- Resamples House 1 readings to one-minute intervals.
- Produces cleaned data and before/after plots.

### Part 2 — Washing-machine EDA

Script: `part2_washing_machine_eda.py`

Uses the official cleaned REFIT files for four households and the appliance mapping from `MetaData_Tables.xlsx`.

| Household | Washing-machine column |
| --------- | ---------------------- |
| House 2   | `Appliance2`           |
| House 5   | `Appliance3`           |
| House 6   | `Appliance2`           |
| House 10  | `Appliance5`           |

Outputs are written to `results/part2/`, including household summaries, detected candidate cycles, usage profiles, and plots.

Cycle detection is heuristic: power greater than 10 W, at least five active minutes, short-gap merging, and a 120-minute duration cutoff. These counts are not verified counts of complete washing programmes.

### Part 3 — Load disaggregation

Script: `part3_disaggregation_model.py`

- Predicts washing-machine power from aggregate power, lagged aggregate readings, rolling aggregate statistics, and time features.
- Compares a zero-load baseline with a Random Forest regressor.
- Uses a chronological 80/20 train/test split within each household.
- Caps model training at 100,000 randomly sampled rows from the training period.
- Writes metrics, prediction CSVs, and actual-versus-predicted plots to `results/part3/`.

The evaluation measures future-period performance for known households. It does not test transfer to a household entirely excluded from training.

## Requirements

Python 3.11 or another Python version supported by the installed scientific Python packages.

Install dependencies in a virtual environment:

```powershell
.venv\Scripts\python.exe -m pip install pandas numpy matplotlib scikit-learn openpyxl
```

## Data Setup

Place the official cleaned household CSVs in:

```text
data/official_cleaned/
```

Expected filenames include `CLEAN_House2.csv`, `CLEAN_House5.csv`, `CLEAN_House6.csv`, and `CLEAN_House10.csv`.

Place raw REFIT House 1 CSV files where the Part 1 script expects them. Check the input paths at the top of each script before running.

Do not commit large raw datasets to a public repository unless their licence and distribution terms explicitly allow it. Include download instructions and citations in `DATA.md` instead.

## Run the Analysis

From the project root in the VS Code terminal:

```powershell
.venv\Scripts\python.exe part1_raw_cleaning.py
.venv\Scripts\python.exe part2_washing_machine_eda.py
.venv\Scripts\python.exe part3_disaggregation_model.py
```

Run each part after confirming its configured input paths.

## Current Results Summary

On the four-household chronological test sets, the Random Forest reduced RMSE compared with the zero baseline for all four houses, but overall MAE was higher for all four. On minutes where actual washing-machine power exceeded 10 W, the Random Forest improved both MAE and RMSE relative to the zero baseline.

This indicates that the model can estimate active-period power better than always predicting zero, but its false activations and missed peaks remain important limitations. See `RESULTS.md` and `Recommendation.md` for details.

## Repository Structure

```text
refit_ds/
├── part1_raw_cleaning.py
├── part2_washing_machine_eda.py
├── part3_disaggregation_model.py
├── README.md
├── DATA.md
├── RESULTS.md
├── Recommendation.md
├── data/
│   ├── official_cleaned/
│   └── cleaned/
└── results/
    ├── part2/
    └── part3/
```

The structure above is a suggested layout; retain your actual filenames and folders if they differ.

## Limitations

- Household files have different amounts of missing data.
- The cycle detector is rule-based and not validated against ground-truth programme boundaries.
- A zero baseline performs strongly on overall MAE because the appliance is inactive for many minutes.
- The Random Forest misses some high-power peaks and can produce false activations.
- The evaluation is within-household over time, not household-independent.

## Data Source

REFIT: Electrical Load Measurements (Cleaned), University of Strathclyde. Cite the dataset in the final report and include the official download page and data-use terms in `DATA.md`.
