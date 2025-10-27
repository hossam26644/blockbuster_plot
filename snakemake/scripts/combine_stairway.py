import os
import yaml
import sys


# Root folder where subdirectories contain demes.yml
root_dir = sys.argv[1]
output_file = sys.argv[2]

combined_demes = []
time_units = None
generation_time = None
# Walk through all subdirectories
for dirpath, dirnames, filenames in os.walk(root_dir):
    files_in_dir = [f for f in filenames if f.startswith("deme_") and f.endswith(".yml")]

    for file in files_in_dir:
        file_path = os.path.join(dirpath, file)
        #file_path = os.path.join(dirpath, f"demes_block{blocks}.yaml")
        with open(file_path) as f:
            data = yaml.safe_load(f)

        # Set time_units (assume all are the same)
        if time_units is None:
            time_units = data.get("time_units")
            generation_time = data.get("generation_time")

        if "demes" in data and len(data["demes"]) == 1:
            deme = data["demes"][0]
            # Use the immediate directory name as the deme name
            deme["name"] = file.replace(".yml", "")
            combined_demes.append(deme)
        else:
            print(f"Warning: {file_path} doesn't contain exactly one deme.")

# Combine into final structure
combined_model = {
    "time_units": time_units,
    "demes": combined_demes,
}
if generation_time is not None:
    combined_model["generation_time"] = generation_time
    print("Generation time set to", generation_time)

# Write the merged output
with open(output_file, "w") as f:
    yaml.dump(combined_model, f, sort_keys=False)

print(f"✅ Combined demes saved to {output_file}")
