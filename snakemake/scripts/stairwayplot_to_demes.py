"""
converts a stairwayplot output file (TSV with 'year' and 'Ne_median' columns)
to a demes YAML format file.
"""
import pandas as pd
import yaml
import sys
import numpy as np

# Input and output files
input_file = sys.argv[1]
output_file = sys.argv[2]

# Load data
df = pd.read_csv(input_file, sep="\t")

grouped = df.groupby("year", as_index=False)["Ne_median"].median()

grouped = grouped.sort_values(by="year", ascending=False).reset_index(drop=True)

years = grouped["year"].tolist()
nes = grouped["Ne_median"].tolist()

epochs = []
n = len(years)
for i in range(n):
    this_year = years[i]
    # end_time is the boundary at the end of this epoch (i.e. start of next younger epoch)
    end_time = years[i + 1] if i + 1 < n else 0.0
    size = float(nes[i])
    epoch = {
        # demes expects end_time (time measured from present)
        "end_time": float(end_time),
        # we set start_size and end_size equal for a constant-size epoch
        "start_size": size,
        "end_size": size,
    }
    epochs.append(epoch)

demes_model = {
    "description": "Population history converted from input file (Ne_median).",
    "time_units": "years",
    "generation_time": 1,
    "demes": [
        {
            "name": "B",
            # the population 'starts' at the oldest time in the file
            "start_time": np.inf,  #float(grouped["year"].max()) if n > 0 else 0.0,
            "epochs": epochs,
        }
    ],
}

# Save as YAML
with open(output_file, "w") as f:
    yaml.dump(demes_model, f, sort_keys=False)

print(f"Stariwayplot output converted to demes format in the YAML file: {output_file}")
