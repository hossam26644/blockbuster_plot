import msprime
import demes
import sys

# Inputs
seed = int(sys.argv[1])
graph_path = sys.argv[2]
sequence_length = int(sys.argv[3])
mutation_rate = float(sys.argv[4])
recombination_rate = float(sys.argv[5])
output_path = sys.argv[6]

# Load demography
graph = demes.load(graph_path)
demography = msprime.Demography.from_demes(graph)

# Simulate tree sequence
ts = msprime.sim_ancestry(
    20,
    random_seed=seed,
    ploidy=1,
    sequence_length=sequence_length,
    recombination_rate=recombination_rate,
    demography=demography,
)
ts = msprime.sim_mutations(ts, rate=mutation_rate, random_seed=seed)

# Get SFS
sfs = ts.allele_frequency_spectrum(polarised=True, span_normalise=False)[1:-1]

# Write output
with open(output_path, "w") as f:
    f.write(" ".join(str(v) for v in sfs) + "\n")
