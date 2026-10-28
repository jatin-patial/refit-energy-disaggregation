## Part 1: Raw Data Cleaning

### Objective

Clean the raw REFIT dataset for House 1 by standardizing timestamps, resampling the power readings to one-minute intervals, and examining missing values, duplicate timestamps, irregular intervals, and extreme readings.

### Cleaning Procedure

- Loaded the raw House 1 electricity consumption data.
- Converted the timestamp column to a consistent datetime format.
- Checked for duplicate timestamps and irregular sampling intervals.
- Resampled the readings to one-minute intervals.
- Identified missing values and examined extreme power readings.
- Generated visualizations to compare the data before and after cleaning.

### Results

The cleaning process prepared the raw data for further analysis by creating a consistent one-minute time series and identifying data-quality issues.

**Note:** Insert the actual missing-value counts, duplicate counts, and before-and-after observations from your Part 1 script output here. These values should be reported from the generated results rather than estimated.

### Limitations

- Resampling can introduce missing values where no original readings are available.
- Extreme readings require investigation before being removed, as they may represent genuine appliance activity.
- The cleaned data may still contain gaps or measurement errors.

# Part 2: Washing-Machine Exploratory Data Analysis

## Dataset and Method

This analysis uses the official cleaned REFIT dataset at one-minute resolution. Four households were selected using the appliance metadata: Houses 2, 5, 6, and 10.

| Household | Washing-machine channel |
| --------- | ----------------------- |
| 2         | Appliance2              |
| 5         | Appliance3              |
| 6         | Appliance2              |
| 10        | Appliance5              |

The original timestamps were parsed, sorted, and deduplicated before resampling to one-minute mean power. Missing readings were retained as missing rather than filled with artificial values.

## Data Availability

| Household | Start      | End        | Missing washer readings |
| --------- | ---------- | ---------- | ----------------------: |
| 2         | 2013-09-17 | 2015-05-28 |                  24.62% |
| 5         | 2013-09-26 | 2015-07-06 |                   9.34% |
| 6         | 2013-11-28 | 2015-06-28 |                  15.25% |
| 10        | 2013-11-20 | 2015-06-30 |                  11.20% |

House 2 has the highest missing-data percentage, while House 5 has the lowest. Missing readings may affect comparisons between households.

## Weekday and Weekend Usage

Mean washing-machine power across valid minutes:

| Household | Weekday | Weekend |
| --------- | ------: | ------: |
| 2         | 18.79 W | 16.30 W |
| 5         | 16.54 W | 68.69 W |
| 6         |  6.01 W |  9.72 W |
| 10        | 33.58 W | 29.61 W |

House 5 has a much higher weekend mean than weekday mean. House 6 has the lowest mean power on both weekdays and weekends. These averages include inactive minutes and should not be interpreted as the power used only during active washing.

## Cycle Detection

A candidate cycle is identified using a threshold of more than 10 W, a minimum of five active minutes, and merging of short inactive gaps. Candidate periods longer than 120 minutes are excluded by the current implementation.

| Household | Detected candidate cycles | Median duration |
| --------- | ------------------------: | --------------: |
| 2         |                       327 |          95 min |
| 5         |                     1,146 |          30 min |
| 6         |                       111 |          26 min |
| 10        |                       533 |          43 min |

These are heuristic estimates, not verified counts of complete washing programmes. The threshold can split one programme into multiple events, while merging short gaps can combine separate events. The 120-minute cutoff also affects the reported duration distribution, particularly for House 10.

## Figures

The `results/part2/` directory contains:

- Aggregate and washing-machine power traces for the first 24 hours of each selected household.
- Example detected cycle plots.
- Hour-of-day mean power profiles.
- A cross-household hourly comparison.

## Limitations

- Missing readings differ across households.
- The cycle threshold and gap-merging rule are heuristic.
- The 120-minute cutoff excludes long candidate periods and can bias duration statistics.
- Mean power includes inactive periods.
- Household differences may reflect data coverage as well as genuine usage differences.

## Conclusion

The four households show different washing-machine usage patterns and data completeness. House 5 has the highest weekend mean power, whereas House 6 has the lowest weekday and weekend means. Cycle statistics should be interpreted cautiously because the detection rule has not been validated against manually verified washing programmes.

## Part 3: Washing-Machine Load Disaggregation

### Objective and Features

A Random Forest regressor was trained to estimate washing-machine power from aggregate household power at one-minute resolution. Input features included aggregate power, lagged aggregate readings, rolling aggregate statistics, and cyclical time-of-day and day-of-week features.

The baseline predicts 0 W at every test timestamp. A chronological 80/20 split was used separately for each household. Model training was limited to 100,000 randomly sampled rows from the training period for computational efficiency.

### Results

| House | Baseline MAE (W) | Model MAE (W) | Baseline RMSE (W) | Model RMSE (W) | Model R² |
| ----- | ---------------: | ------------: | ----------------: | -------------: | -------: |
| 2     |            19.61 |         29.06 |            179.58 |         146.66 |    0.325 |
| 5     |            39.50 |         49.90 |            213.26 |         195.79 |    0.127 |
| 6     |             6.43 |          7.60 |             97.03 |          60.16 |    0.614 |
| 10    |            31.11 |         37.54 |            208.00 |         162.65 |    0.375 |

### Interpretation

The Random Forest reduced RMSE for all four households, but increased MAE relative to the zero-load baseline. This indicates that it reduced some large errors but did not improve average absolute error. House 6 achieved the strongest R² (0.614), while House 5 achieved the weakest (0.127).

### Limitations

- The zero baseline is strong when the washing machine is inactive for most minutes.
- Performance varies between households.
- Training was capped at 100,000 randomly sampled training rows.
- The evaluation tests later periods from households represented in training; it does not measure transfer to an unseen household.
- Actual-versus-predicted plots should be inspected to identify missed peaks, false activations, and underestimation of high-power events.

### Active-Period Evaluation

To assess performance when the washing machine was operating, the model was evaluated separately on test minutes where actual washing-machine power exceeded 10 W.

| House | Active test minutes | Zero-baseline MAE (W) | Model MAE (W) | Zero-baseline RMSE (W) | Model RMSE (W) |
| ----- | ------------------: | --------------------: | ------------: | ---------------------: | -------------: |
| 2     |               6,579 |                383.92 |        276.84 |                 796.00 |         566.10 |
| 5     |              19,054 |                334.55 |        295.65 |                 621.07 |         549.04 |
| 6     |               2,388 |                365.09 |        178.63 |                 731.64 |         396.61 |
| 10    |              12,322 |                363.54 |        255.07 |                 711.31 |         487.83 |

The Random Forest reduces both MAE and RMSE during active periods for all four households. Active-period MAE improves by approximately 27.9% for House 2, 11.6% for House 5, 51.1% for House 6, and 29.8% for House 10, relative to the zero baseline.

This contrasts with the full test-set results, where model MAE is worse than the zero baseline. The difference suggests that the baseline benefits from the large number of inactive minutes, while the Random Forest provides useful—but imperfect—estimates during washing-machine activity.

### Failure Cases

Inspection of the House 5 actual-versus-predicted plot reveals missed high-power peaks, false predicted spikes, and imperfect alignment between actual and predicted events. These errors indicate that aggregate power alone does not always identify washing-machine activity reliably when other household loads overlap.

The active-period results are conditional on actual power exceeding 10 W; they evaluate power estimation during known active minutes rather than the ability to detect those minutes in advance.
