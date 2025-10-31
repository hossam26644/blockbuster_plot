import os
import yaml
import sys


# Root folder where subdirectories contain demes.yml
root_dir = sys.argv[1]
blocks = int(sys.argv[2])
output_file = sys.argv[3]

combined_demes = []
time_units = None

# Walk through all subdirectories
for dirpath, dirnames, filenames in os.walk(root_dir):
    if f"{blocks}_epochs.yml" in filenames:
        file_path = os.path.join(dirpath, f"{blocks}_epochs.yml")
        with open(file_path) as f:
            data = yaml.safe_load(f)

        # Set time_units (assume all are the same)
        if time_units is None:
            time_units = data.get("time_units", "generations")

        if "demes" in data and len(data["demes"]) == 1:
            deme = data["demes"][0]
            
            name = file_path.split("/")[-3]
            deme["name"] = os.path.basename(name)
            combined_demes.append(deme)
        else:
            print(f"Warning: {file_path} doesn't contain exactly one deme.")

# Combine into final structure
combined_model = {
    "time_units": time_units,
    "demes": combined_demes
}

# Write the merged output
with open(output_file, "w") as f:
    yaml.dump(combined_model, f, sort_keys=False)

print(f"✅ Combined demes saved to {output_file}")
