import sys
import demes
import demesdraw
import matplotlib.pyplot as plt


demesfile = sys.argv[1]
original_graph = sys.argv[2]
output_file = sys.argv[3]

replicates = demes.load(demesfile)
original = demes.load(original_graph)

# Create figure with 2 subplots side-by-side
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6), sharey=True)

# Panel 1: Replicates
demesdraw.size_history(replicates, ax=ax1, log_time=True, colours='red')
ax1.set_title("Replicates")

# Panel 2: Original
demesdraw.size_history(original, ax=ax2, log_time=True, colours='blue')
ax2.set_title("Original")

# Panel 3: Overlay
demesdraw.size_history(replicates, ax=ax3, log_time=True, colours='red')
demesdraw.size_history(original, ax=ax3, log_time=True, colours='blue')
ax3.set_title("Overlay")

# Final layout and save
fig.tight_layout()
fig.savefig(output_file, bbox_inches='tight', dpi=300)
plt.close(fig)