# Recommendations

## 1. Data Cleaning

- Resample raw REFIT readings to a consistent one-minute interval.
- Inspect missing timestamps, duplicate readings, and extreme values before modelling.
- Document cleaning decisions and retain the original data unchanged.

## 2. Washing-Machine Usage Analysis

- Compare washing-machine usage across households and by hour and day type.
- Treat detected cycles as heuristic candidates rather than confirmed complete wash cycles.
- Investigate long detected cycles, especially where durations reach the 120-minute detection limit.

## 3. Appliance Disaggregation

- Use chronological train-test splits to avoid training on future observations.
- Compare machine-learning predictions against a zero-power baseline.
- Evaluate both overall performance and periods when the washing machine is active.
- Improve detection of appliance start times and high-power peaks, and investigate false activations.

## 4. Future Improvements

- Test additional models and tune their parameters using training data only.
- Consider appliance-specific temporal features and event-based evaluation.
- Report MAE, RMSE, and R² together because no single metric captures all model errors.
- Validate detected washing cycles against appliance behaviour before treating them as ground truth.

## Limitations

The analysis depends on data quality, appliance-channel mapping, and heuristic cycle detection. Results should be interpreted as exploratory findings rather than definitive measurements of every washing cycle.
