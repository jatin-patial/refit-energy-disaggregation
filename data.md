# Data Cleaning — REFIT House 1

## Dataset and Coverage

- Dataset: REFIT Electrical Load Measurements.
- Household: House 1.
- Files: `RAW_House1_Part1.csv` and `RAW_House1_Part2.csv`.
- Combined timestamp coverage: 9 October 2013 to 10 July 2015.
- Original readings contain `Time`, `Unix`, `Aggregate`, and `Appliance1` through `Appliance9`.
- Power readings are treated as watts.

## Cleaning Steps

1. Parsed `Time` as datetime and removed invalid timestamps.
2. Sorted readings chronologically.
3. Removed duplicate timestamps, retaining the first occurrence.
4. Combined the two parts and checked for duplicates across the combined dataset.
5. Resampled power readings to one-minute intervals using the mean.
6. Kept unavailable readings as missing rather than automatically replacing them with zero.

## Findings

### Part 1

- Original rows: 4,377,877.
- Rows after timestamp deduplication: 3,732,363.
- Invalid timestamps: 0.
- Missing cells were not detected in the original Part 1 inspection.
- The largest observed time gap was approximately 41.6 days.

### Part 2

- Original rows: 4,140,886.
- Duplicate timestamps within Part 2: 0.
- Invalid timestamps: 0.

### Combined Data

- Rows before cross-file deduplication: 7,873,249.
- Duplicate timestamps removed: 116,037.
- Rows after deduplication: 7,757,212.
- One-minute rows: 920,031.
- Completely empty minutes: 115,078.
- Appliance columns have different missing-value counts, with the highest count in Appliance9.

## Limitations and Remaining Checks

- The rule of keeping the first row at duplicate timestamps may discard valid readings when duplicate rows have different missing values. This needs further validation.
- Very high power readings require investigation before they can be classified as erroneous.
- Long gaps should be flagged rather than interpolated.
- The sampling interval is irregular, so resampling can change the representation of short-duration power events.
- Appliance channel identities should be confirmed from the dataset documentation before appliance-specific interpretation.
