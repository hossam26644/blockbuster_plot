import tskit
import msprime

ts = msprime.sim_ancestry(20, random_seed=3, ploidy=1, sequence_length=10000, recombination_rate=0.0001, population_size=1000)
ts = msprime.sim_mutations(ts, rate=0.0001, random_seed=2)
#ts.draw_svg()

sfs = ts.allele_frequency_spectrum(polarised=True, span_normalise=False)[1:-1]
print("SFS:", sfs)

#export array to sfs_new.blk separated by spaces
with open("sfs_new.blk", "w") as f:
    for value in sfs:
        f.write(f"{value} ")
    f.write("\n")

