import os
import yaml
import sys
import pandas as pd

# Root folder where subdirectories contain demes.yml
root_dir = sys.argv[1]
blocks = int(sys.argv[2])
output_file = sys.argv[3]

combined_demes = []
time_units = None

def ne_to_generations(data):
    assert len(data["demes"]) == 1, "Expected exactly one deme for Ne to generations conversion."

    deme = data["demes"][0]
    epochs = deme["epochs"]
    
    epochs = pd.DataFrame(epochs)
    epochs = epochs.sort_values(by="end_time", ascending=False).reset_index(drop=True)
    epochs["size_after"] = epochs["start_size"].shift(-1)
    epochs.at[len(epochs)-1, "size_after"] = 1
    epochs["end_time"] = epochs["size_after"] * epochs["end_time"]
    #epochs["end_time"] = epochs["start_size"] * epochs["end_time"]

    deme["epochs"] = epochs[["start_size", "end_time"]].to_dict(orient="records")

    data["demes"] = [deme]
    return data

time_units = None
# Walk through all subdirectories
for dirpath, dirnames, filenames in os.walk(root_dir):
    if f"{blocks}_epochs.yml" in filenames:
        file_path = os.path.join(dirpath, f"{blocks}_epochs.yml")
        with open(file_path) as f:
            data = yaml.safe_load(f)

        assert time_units is None or time_units == data["time_units"], "Inconsistent time units across files."
        time_units = data["time_units"]

        if time_units == "Ne generations":
            data["time_units"] = "generations"
            data = ne_to_generations(data)
        if "demes" in data and len(data["demes"]) == 1:
            deme = data["demes"][0]
            
            name = file_path.split("/")[-3]
            deme["name"] = os.path.basename(name)
            combined_demes.append(deme)
        else:
            print(f"Warning: {file_path} doesn't contain exactly one deme.")

# Combine into final structure
combined_model = {
    "time_units": "generations",
    "demes": combined_demes
}

# Write the merged output
with open(output_file, "w") as f:
    yaml.dump(combined_model, f, sort_keys=False)

print(f"✅ Combined demes saved to {output_file}")
