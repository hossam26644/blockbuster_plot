import sys
import yaml
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from copy import deepcopy

demesfile = sys.argv[1]      # combined_demes.yml
original_graph = sys.argv[2] # graph.yml
output_file = sys.argv[3]    # output figure

def add_points_to_make_line_plots_look_like_demes(end_time, start_size):

    end_time = end_time.T; start_size = start_size.T
    new_time = []; new_size = []
    first_row = deepcopy(end_time[0])
    first_row["mean"] = first_row["mean"] * 2
    new_time.append(first_row)
    new_size.append(start_size[0])

    for i in range(len(end_time.T) - 1):
        time_row = end_time[i]
        size_row = start_size[i]
        new_time.append(time_row)
        new_time.append(time_row)
        new_size.append(size_row)
        new_size.append(start_size[i+1])

    new_time.append(end_time[len(end_time.T) - 1])
    new_size.append(start_size[len(start_size.T) - 1])

    return pd.DataFrame(new_time), pd.DataFrame(new_size)

def add_points_to_make_line_plots_look_like_demes_dff(df):
    new_rows = []
    first_row = deepcopy(df.iloc[0])
    first_row["end_time"] = first_row["end_time"] * 2
    new_rows.append(first_row)

    for i in range(len(df) - 1):
        new_rows.append(deepcopy(df.iloc[i]))
        row = deepcopy(df.iloc[i])
        row['start_size'] = df.iloc[i + 1]['start_size']
        new_rows.append(row)

    new_rows.append(df.iloc[-1])
    return pd.DataFrame(new_rows)

with open(demesfile, "r") as f:
    combined = yaml.safe_load(f)

with open(original_graph, "r") as f:
    original = yaml.safe_load(f)

# ------------------------
# Convert replicate demes into DataFrame
# ------------------------
records = []
for deme in combined["demes"]:
    for i, epoch in enumerate(deme["epochs"]):
        records.append({
            "deme": deme["name"],
            "epoch": i,
            "start_size": epoch["start_size"],
            "end_time": epoch["end_time"],
        })

df = pd.DataFrame(records)

# ------------------------
# Compute quantiles & averages
# ------------------------
end_time_df = (
    df.groupby("epoch")["end_time"]
    .agg([
        ("mean", "mean"),
        ("q05", lambda x: np.quantile(x, 0.05)),
        ("q95", lambda x: np.quantile(x, 0.95))
    ])
    .reset_index()
)
start_size_df = (
    df.groupby("epoch")["start_size"]
    .agg([
        ("mean", "mean"),
        ("q05", lambda x: np.quantile(x, 0.05)),
        ("q95", lambda x: np.quantile(x, 0.95))
    ])
    .reset_index()
)
end_time_df.to_csv(output_file.replace(".png", "_end_time.csv"), index=False)

end_time_df, start_size_df = add_points_to_make_line_plots_look_like_demes(end_time_df, start_size_df)

# For plotting: also extract theoretical deme
theoretical = []
for i, epoch in enumerate(original["demes"][0]["epochs"]):
    theoretical.append({
        "epoch": i,
        "start_size": epoch["start_size"],
        "end_time": epoch["end_time"],
    })
theoretical_df = pd.DataFrame(theoretical)

theoretical_df = add_points_to_make_line_plots_look_like_demes_dff(theoretical_df)

fig, ax = plt.subplots(figsize=(8, 6))

# Plot mean line
ax.plot(end_time_df["mean"], start_size_df["mean"],
        color="red", lw=2, label="Average")

# Plot CI shading
ax.fill_betweenx(start_size_df["mean"],
                 end_time_df["q05"], end_time_df["q95"],
                 color="gray", alpha=0.3, label="5–95% CI")

# Plot theoretical line
ax.plot(theoretical_df["end_time"], theoretical_df["start_size"],
        color="blue", lw=2, label="Theoretical")

ax.set_xlabel("Time (generations)")
ax.set_ylabel("Population size")
ax.set_xscale("log")  # log time axis, like demesdraw
ax.set_yscale("log")
ax.invert_xaxis()  # time flows forward (∞ → 0)
ax.legend()

fig.tight_layout()
fig.savefig(output_file, dpi=300)
plt.close(fig)

print("✅ Figure saved to", output_file)