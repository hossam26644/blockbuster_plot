import msprime
import demes
import sys
from distutils.util import strtobool
import yaml

# Inputs
settings_file = str(sys.argv[1])
seed = int(sys.argv[2])

settings_json = yaml.safe_load(open(settings_file, "r"))
graph_path = settings_json["graph"]
sequence_length = settings_json["sequence_length"]
mutation_rate = settings_json["mutation_rate"]
recombination_rate = settings_json["recombination_rate"]
output_path = str(settings_json["output_dir"])+f"/sfss/sfs_{seed}.blk"
branch_sfs = strtobool(str(settings_json["branch_sfs"]))
k = settings_json["k"]

graph = demes.load(graph_path)
demography = msprime.Demography.from_demes(graph)

if int(k) < int(sequence_length):
    model = msprime.SmcKApproxCoalescent(hull_offset=k)
else:
    model = None

print(f"Simulating SFS with seed {seed} and k={k} (branch_sfs={branch_sfs}), model={model}")
# Simulate tree sequence
ts = msprime.sim_ancestry(
    10,
    random_seed=seed,
    ploidy=2,
    sequence_length=sequence_length,
    recombination_rate=recombination_rate,
    demography=demography,
    model=model
)

if not branch_sfs:
    print("Adding mutations to tree sequence")
    ts = msprime.sim_mutations(ts, rate=mutation_rate, random_seed=seed, discrete_genome=False)

mode = "branch" if branch_sfs else "site"
# Get SFS
sfs = ts.allele_frequency_spectrum(polarised=True, span_normalise=branch_sfs, mode=mode)[1:-1]

# Write output
with open(output_path, "w") as f:
    f.write(" ".join(str(v) for v in sfs) + "\n")
