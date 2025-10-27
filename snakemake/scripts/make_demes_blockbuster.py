import sys
import os
import yaml
import numpy as np

def parse_blocks(file_path):
    blocks = {}
    current_block = None
    eff_sizes = []
    times = []

    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith('>') and line.endswith("blocks"):
                # new block section
                current_block = int(line.split()[1])
                eff_sizes = []
                times = []

            elif line.startswith("Effective size (Ne):"):
                sizes = line.split("Times of change in generations:")[0].strip()
                eff_sizes.extend([float(x) for x in sizes.split(":")[1].split()])

                times_list = line.split("Times of change in generations:")[1].strip()
                times.extend([float(x) for x in times_list.split()])
                times = times[::-1]
                times.append(0)  # Add present time
                blocks[current_block] = {"eff_sizes": eff_sizes[::-1], "times": times}

    return blocks


def make_demes_yaml(eff_sizes, times):
    epochs = []
    for t, size in zip(times, eff_sizes):
        epochs.append({"start_size": size, "end_time": t})

    return {
        "time_units": "generations",
        "demes": [
            {
                "name": "B",
                "start_time": np.inf,
                "epochs": epochs
            }
        ]
    }


prediction_dir = sys.argv[1]
run_no = sys.argv[2]
input_file = f'{prediction_dir}/test_blockbuster{run_no}/parsed_output.txt'
blocks = parse_blocks(input_file)

for block_id, data in blocks.items():
    demes_yaml = make_demes_yaml(data["eff_sizes"], data["times"])
    out_file = f"{prediction_dir}/test_blockbuster{run_no}/demes_block{block_id}.yaml"
    with open(out_file, "w") as out_f:
        yaml.dump(demes_yaml, out_f, sort_keys=False)

