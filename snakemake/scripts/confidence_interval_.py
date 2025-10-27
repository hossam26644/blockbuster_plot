import sys
import yaml
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from copy import deepcopy
import matplotlib.patches as patches
import math
import demes
import demesdraw

demesfile = sys.argv[1]      # combined_demes.yml
original_graph = sys.argv[2] # graph.yml
output_file = sys.argv[3]    # output figure

with open(demesfile, "r") as f:
    combined = yaml.safe_load(f)

with open(original_graph, "r") as f:
    original = yaml.safe_load(f)

demes_df = pd.DataFrame()
for deme in combined["demes"]:
    records = []

    for i, epoch in enumerate(deme["epochs"]):
        records.append({
            "deme": deme["name"],
            "start_size": epoch["start_size"],
            "end_time": epoch["end_time"],
        })

    df = pd.DataFrame(records)
    #sort first by end_time and add epoch number
    df = df.sort_values(by=["end_time"], ascending=False).reset_index(drop=True)
    df["epoch"] = df.index
    #add start_time column
    # start_time of epoch i is end_time of epoch i-1, except for epoch 0 which is inf
    df["start_time"] = df["end_time"].shift(1)
    df.loc[0, "start_time"] = np.inf

    demes_df = pd.concat([demes_df, df], ignore_index=True)
fig, ax = plt.subplots(figsize=(8, 6))
original = demes.load('snakemake/DroMel_OOF.yaml')
#demesdraw.size_history(original, ax=ax, log_time=True, colours='blue', log_size=True)


for i, epoch in enumerate(demes_df["epoch"].unique()):
    print("Epoch", epoch)
    sizes = demes_df[demes_df["epoch"] == epoch]["start_size"]
    start_times = demes_df[demes_df["epoch"] == epoch]["start_time"]
    end_times = demes_df[demes_df["epoch"] == epoch]["end_time"]

    size_perc5 =  np.percentile(sizes, 5) #min(sizes)
    size_perc95 = np.percentile(sizes, 95) #max(sizes)
    start_time_perc5 =  np.percentile(start_times, 95) #max(start_times)
    end_time_perc95 = np.percentile(end_times, 5) #min(end_times)

    if math.isnan(start_time_perc5) or np.isinf(start_time_perc5):
        start_time_perc5 = max(demes_df["end_time"].replace(np.inf, np.nan).dropna()) * 10
    # Create a Rectangle patch
    rectangle = patches.Rectangle((end_time_perc95, size_perc5),
        start_time_perc5 - end_time_perc95, #rect_width
        size_perc95 - size_perc5, #rect_height
        linewidth=1, facecolor='grey', alpha=0.3,)

    ax.add_patch(rectangle)






ax.set_xlabel("Time (generations)")
ax.set_ylabel("Population size")
ax.set_xscale("log")  # log time axis, like demesdraw
ax.set_yscale("log")
#ax.invert_xaxis()  # time flows forward (∞ → 0)
#ax.legend()
ax.set_xlim(0.01, 1e7)
ax.set_ylim(0.01, 1e8)

#fig.tight_layout()
fig.savefig(output_file, dpi=300)
plt.close(fig)

print("✅ Figure saved to", output_file)
