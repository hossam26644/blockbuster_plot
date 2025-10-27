import sys
import demes
import demesdraw
import matplotlib.pyplot as plt


demesfile = sys.argv[1]
original_graph = sys.argv[2]
output_file = sys.argv[3]

replicates = demes.load(demesfile)
original = demes.load(original_graph)
log_time = True

def uniformise(ax, linewidth=2, linestyle='-'):
    # remove legend if present
    leg = ax.get_legend()
    if leg:
        leg.remove()
    # demesdraw.size_history uses PathPatch objects (not Line2D)
    for p in ax.patches:
        p.set_linestyle(linestyle)  # make discontinuities solid too
        p.set_linewidth(linewidth)  # same width for all demes
        # optional: remove the white halo for perfectly uniform look
        try:
            p.set_path_effects([])
        except Exception as e:
            print(f"Warning: could not remove path effects: {e}")


# Create figure with 2 subplots side-by-side
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6), sharey=True, sharex=True)

# Panel 1: Replicates
demesdraw.size_history(replicates, ax=ax1, log_time=log_time, colours='red', log_size=True)
ax1.set_title("Replicates")
uniformise(ax1, linewidth=2, linestyle='-')

# Panel 2: Original
demesdraw.size_history(original, ax=ax2, log_time=log_time, colours='blue', log_size=True)
ax2.set_title("Original")
uniformise(ax2, linewidth=2, linestyle='-')

# Panel 3: Overlay
demesdraw.size_history(replicates, ax=ax3, log_time=log_time, colours='red', log_size=True)
demesdraw.size_history(original, ax=ax3, log_time=log_time, colours='blue', log_size=True)
ax3.set_title("Overlay")
uniformise(ax3, linewidth=2, linestyle='-')

# Final layout and save
fig.tight_layout()
fig.savefig(output_file, bbox_inches='tight', dpi=300)
plt.close(fig)