import yaml
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Dict, Tuple
import argparse
import os 
from matplotlib.patches import Patch
import similaritymeasures # pip install similaritymeasures

class SingleDeme:
    def __init__(self, deme_dict: Dict):
        self.name = deme_dict['name']
        self.deme_dict = deme_dict
        self.epochs = self.get_epochs()
        self.time_points = self._extract_time_points()
        self.sizes = self.get_sizes()
        
    def get_epochs(self) -> List[Dict]:
        """Parse deme epochs into a structured format."""  
        epochs = []
        prev_time = float('inf')
        
        for epoch in self.deme_dict['epochs']: 
            end_time = epoch['end_time']
            start_size = epoch['start_size']
            
            epochs.append({
                'start_time': prev_time,
                'end_time': end_time,
                'size': start_size
            })
            prev_time = end_time
        #sort epochs by end_time descending
        epochs = sorted(epochs, key=lambda x: x['end_time'], reverse=True)
        return epochs

    def _extract_time_points(self) -> List[float]:
        """Extract all unique time points and sort them."""
        time_points = set()
        
        for epoch in self.epochs:
            if epoch['end_time'] != float('inf'):
                time_points.add(epoch['end_time'])
            if epoch['start_time'] != float('inf'):
                time_points.add(epoch['start_time'])                
        
        return sorted([t for t in time_points if t != float('inf')], reverse=True)

    def get_sizes(self) -> List[float]:
        """Get population sizes at each time point."""
        sizes = []
        for epoch in self.epochs:
            sizes.append(epoch['size'])
        return sizes

class DemesAnalyzer:
    
    def __init__(self, demes_file=None, min_time=0, max_time=float('inf'), deme_data=None):
        """
        Initialize with a demes file.
        
        Args:
            demes_file: Path to YAML file or YAML string
        """
        if demes_file is not None:
            self.data = self._load_yaml(demes_file)
            self.deme_data = self._parse_demes()
        if deme_data is not None:
            self.deme_data = deme_data

        self.time_points = self._extract_time_points()
        self._total_envelope_area = None
        self.min_time = min_time
        self.max_time = max_time
        
    def _load_yaml(self, demes_file) -> Dict:
        """Load YAML from file or string."""
        if isinstance(demes_file, str) and '\n' in demes_file:
            return yaml.safe_load(demes_file)
        else:
            with open(demes_file, 'r') as f:
                return yaml.safe_load(f)
    
    def _parse_demes(self) -> List[SingleDeme]:  
        """Parse deme epochs into a structured format."""
        return [SingleDeme(deme) for deme in self.data['demes']]
            
    def _extract_time_points(self, deme_data=None) -> List[float]:
        """Extract all unique time points and sort them."""
        time_points = set()
        
        if deme_data is None:
            deme_data = self.deme_data
        for deme in deme_data:
            time_points.update(deme.time_points)
        time_points.add(max(time_points)*3)
        return sorted([t for t in time_points if t != float('inf')], reverse=True)
        
    def _get_sizes_at_interval(self, t_start: float, t_end: float, deme_data=None) -> List[float]:
        """Get population sizes for all demes in a time interval."""
        
        if deme_data is None:
            deme_data = self.deme_data
        sizes = []
        for deme in deme_data:
            for epoch in deme.epochs:
                if epoch['start_time'] >= t_start and epoch['end_time'] <= t_end:
                    sizes.append(epoch['size'])
                    break
        
        return sizes
      
    @property
    def total_envelope_area(self) -> float:
        """Calculate and cache total envelope area."""
        if self._total_envelope_area is None:
            self._total_envelope_area = self.calculate_envelope_area()
        return self._total_envelope_area

    def calculate_envelope_area(self, lower_percentile: float = 2.5, 
                                upper_percentile: float = 97.5) -> float:
        """
        Calculate total area between percentile envelopes.
        
        Args:
            lower_percentile: Lower percentile boundary (default 2.5)
            upper_percentile: Upper percentile boundary (default 97.5)
        
        Returns:
            Total area between envelopes
        """
        total_area = 0.0
        
        for i in range(len(self.time_points) - 1):
            t_start = self.time_points[i]
            t_end = self.time_points[i + 1]

            if t_end < self.min_time or t_start > self.max_time:
                continue

            interval_width = t_start - t_end
            
            sizes = self._get_sizes_at_interval(t_start, t_end)
            
            if sizes:
                p_upper = np.percentile(sizes, upper_percentile)
                p_lower = np.percentile(sizes, lower_percentile)
                height = p_upper - p_lower
                area = interval_width * height
                total_area += area
        
        return total_area
    
    def get_envelope_data(self, lower_percentile: float = 2.5,
                         upper_percentile: float = 97.5) -> Tuple[np.ndarray, ...]:
        """
        Get time series data for mean and percentile envelopes.
        Returns stepwise data where each interval maintains constant values.
        
        Args:
            lower_percentile: Lower percentile boundary (default 2.5)
            upper_percentile: Upper percentile boundary (default 97.5)
        
        Returns:
            Tuple of (times, means, lower_bounds, upper_bounds)
        """
        times = []
        means = []
        lower_bounds = []
        upper_bounds = []
        
        for i in range(len(self.time_points) - 1):
            t_start = self.time_points[i]
            t_end = self.time_points[i + 1]

            if t_end < self.min_time or t_start > self.max_time:
                continue
            
            sizes = self._get_sizes_at_interval(t_start, t_end)
            
            if sizes:
                mean_val = np.mean(sizes)
                lower_val = np.percentile(sizes, lower_percentile)
                #lower_val = min(sizes)
                upper_val = np.percentile(sizes, upper_percentile)
                #upper_val = max(sizes)
                
                # Add both start and end points for this interval
                times.extend([t_start, t_end])
                means.extend([mean_val, mean_val])
                lower_bounds.extend([lower_val, lower_val])
                upper_bounds.extend([upper_val, upper_val])
        
        return (np.array(times), np.array(means), 
                np.array(lower_bounds), np.array(upper_bounds))


class EnvelopePlotter:
    """Analyze and visualize population size envelopes from demes YAML files."""
    
    def __init__(self, combined_simulations_file, original_deme_file):
        self.original = DemesAnalyzer(original_deme_file)
        self.min_time = min(self.original.time_points)
        self.max_time = max(self.original.time_points)
        self.combined_simulations = DemesAnalyzer(combined_simulations_file,
            min_time=self.min_time, max_time=self.max_time)   

    def plot_envelope(self, lower_percentile: float = 2.5,
                     upper_percentile: float = 97.5,
                     figsize: Tuple[int, int] = (10, 6),
                     plot_file_name: str = "deme_envelope_plot.png"):
        """
        Plot population size with percentile envelope.
        
        Args:
            lower_percentile: Lower percentile boundary (default 2.5)
            upper_percentile: Upper percentile boundary (default 97.5)
            figsize: Figure size as (width, height)
        """

        times, means, lower, upper = self.combined_simulations.get_envelope_data(
            lower_percentile, upper_percentile
        )
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # Plot envelope (gray shaded region)
        ax.fill_between(times, lower, upper, alpha=0.3, color='gray', 
                        label=f'{lower_percentile}th-{upper_percentile}th percentile')

        orig_times, orig_means, _, _ = self.original.get_envelope_data(0, 100)
        ax.plot(orig_times, orig_means, color='blue', linewidth=2, label='Original deme')
        
        # Plot mean line
        ax.plot(times, means, linestyle="--"  ,color='black', linewidth=2, label='Mean', alpha=0.7)
        
        ax.set_xlabel('Time (generations)', fontsize=12)
        ax.set_ylabel('Population Size', fontsize=12)
        ax.set_xscale('log')
        ax.set_title('Population Size Envelope Across Demes', fontsize=14, fontweight='bold')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        
        # Reverse x-axis to show time going forward
        #ax.invert_xaxis()
        
        plt.tight_layout()
        plt.savefig(plot_file_name)

class BoxPlotter:
    
    def __init__(self, successful_runs: List[str], original_deme_file: str, prefix: str = ""):
        self.successful_runs = successful_runs
        self.original = DemesAnalyzer(original_deme_file)
        self.min_time = min(self.original.time_points)
        self.max_time = max(self.original.time_points)

        #dir_path = os.path.dirname(os.path.realpath(__file__))
        self.deme_per_seq = {s: DemesAnalyzer(f"{prefix}_seq_{s}/results.yml", min_time=self.min_time, max_time=self.max_time) for s in successful_runs}        

    def mean_errors_between_time_points(self,  start_time: float, end_time: float,
        t_scale_start:float = None, t_scale_end:float = None) -> Dict[str, List[float]]:
        """
        Calculate MSE errors between the demes of this demes analyzer and the original deme,
        between specified time points.
        Args:
            start_time: Start time for MSE calculation
            end_time: End time for MSE calculation
        Returns:
            List of MSE errors for each deme
        
        """
        mean_errors = {}
        rmse_errors = {}
        if t_scale_start is None:
            t_scale_start = start_time
        if t_scale_end is None:
            t_scale_end = end_time

        for seq, deme_per_seq in self.deme_per_seq.items():
            for deme in deme_per_seq.deme_data:
                time_points = deme_per_seq._extract_time_points(deme_data=[deme])

                for i in range(len(deme_per_seq.time_points) - 1):
                    t_start = deme_per_seq.time_points[i]
                    t_end = deme_per_seq.time_points[i + 1]
                    #scale is the ratio between the time between the time points and the time between start and end
                    scale = (t_start - t_end) / (t_scale_end - t_scale_start)
                    if t_end < deme_per_seq.min_time or t_start > deme_per_seq.max_time:
                        continue

                    if t_end < start_time or t_start > end_time:
                        continue
                    t_start = max(t_start, start_time) #TODO add this to envelope
                    t_end = min(t_end, end_time)

                    sizes = deme_per_seq._get_sizes_at_interval(t_start, t_end, deme_data=[deme])
                    assert len(sizes) == 1, "Expected exactly one size for the deme in the interval."
                    size = sizes[0]

                    orig_sizes = self.original._get_sizes_at_interval(t_start, t_end)

                    assert len(orig_sizes) == 1, "Expected exactly one size for the original deme in the interval."
                    orig_size = orig_sizes[0]
                    me = (size - orig_size)
                    if seq not in mean_errors:
                        mean_errors[seq] = []
                    mean_errors[seq].append(me*scale)
                
        return mean_errors            

    def frechet_dist(self) -> Dict[str, List[float]]:
        from scipy import interpolate

        original_breakpoints = self.original.deme_data[0].time_points
        original_sizes = self.original.deme_data[0].sizes
        area_diffs = {}
        for seq, deme_per_seq in self.deme_per_seq.items():
            for deme in deme_per_seq.deme_data:
                deme_breakpoints = deme.time_points
                deme_sizes = deme.sizes
                breakpoints_min = max(min(original_breakpoints), min(deme_breakpoints))
                breakpoints_max = min(max(original_breakpoints), max(deme_breakpoints))

                if breakpoints_min ==0:
                    breakpoints_min = 1
                common_breakpoints = np.logspace(
                    np.log10(breakpoints_min),
                    np.log10(breakpoints_max-1),
                    100)

                orig_interp = interpolate.interp1d(original_breakpoints, original_sizes, kind='nearest')(common_breakpoints)
                deme_interp = interpolate.interp1d(deme_breakpoints, deme_sizes, kind='nearest')(common_breakpoints)

                line_orig = np.column_stack((common_breakpoints, orig_interp))
                line_deme = np.column_stack((common_breakpoints, deme_interp))

                area_diff = similaritymeasures.frechet_dist(line_orig, line_deme)
                if seq not in area_diffs:
                    area_diffs[seq] = []
                area_diffs[seq].append(area_diff)
        return area_diffs
         
    def error_mean_bootsrap(self, n_bootstrap: int = 100) -> Dict[str, List[float]]:
        from scipy import interpolate

        errors_per_seq = {}
        original_times, original_means, _, _ = self.original.get_envelope_data()
        for seq, deme_per_seq in self.deme_per_seq.items():
            for t in range(n_bootstrap):
                boots = np.random.choice(deme_per_seq.deme_data, len(deme_per_seq.deme_data), replace=True)
                boot_deme = DemesAnalyzer(deme_data=boots, min_time=self.min_time, max_time=self.max_time)
                boot_times, boot_means, _, _ = boot_deme.get_envelope_data()
                times_min = max(min(original_times), min(boot_times))
                times_max = min(max(original_times), max(boot_times))
                if times_min ==0:
                    times_min = 1               
                times_common = np.logspace(
                    np.log10(times_min),
                    np.log10(times_max-1),
                    100)
                orig_interp = interpolate.interp1d(original_times, original_means, kind='nearest')(times_common)
                boot_interp = interpolate.interp1d(boot_times, boot_means, kind='nearest')(times_common)
                line_orig = np.column_stack((times_common, orig_interp))
                line_boot = np.column_stack((times_common, boot_interp))
                area_diff = similaritymeasures.frechet_dist(line_orig, line_boot)
                if seq not in errors_per_seq:
                    errors_per_seq[seq] = []
                errors_per_seq[seq].append(np.mean(area_diff))
        return errors_per_seq

    def sizes_in_a_time_window(self,  start_time: float, end_time: float) -> Dict[str, List[float]]:
        """
        Calculate MSE errors between the demes of this demes analyzer and the original deme,
        between specified time points.
        Args:
            start_time: Start time for MSE calculation
            end_time: End time for MSE calculation
        Returns:
            List of MSE errors for each deme
        
        """
        sizes_per_seq = {}

        for seq, deme_per_seq in self.deme_per_seq.items():
            sizes_per_seq[seq] = []
            for deme in deme_per_seq.deme_data:
                sizes_per_epoch = []
                scales = []
                for epoch in deme.epochs:
                    e_start = epoch['start_time']
                    e_end = epoch['end_time']

                    if not max(e_end, end_time) <= min(e_start, start_time):
                        s=1
                        continue
                    
                    e_start = min(e_start, start_time) #TODO add this to envelope
                    e_end = max(e_end, end_time) #since we go backwards in time

                    sizes = deme_per_seq._get_sizes_at_interval(e_start, e_end, deme_data=[deme])
                    assert len(sizes) == 1, "Expected exactly one size for the deme in the interval."
                    size = sizes[0]

                    orig_sizes = self.original._get_sizes_at_interval(e_start, e_end)
                    assert len(orig_sizes) == 1, "Expected exactly one size for the original deme in the interval."
                    orig_size = orig_sizes[0]
                    
                    sizes_per_epoch.append(size)
                    scales.append((e_start - e_end) / (start_time - end_time))
                    #scales.append(1)
                
                
                if len(scales) >1:
                    s=1
                scaled_size = sum([(s * scale)/np.sum(scales) for s, scale in zip(sizes_per_epoch, scales)])
                sizes_per_seq[seq].append(scaled_size)
        
        return sizes_per_seq  

    def rmse(self) -> Dict[str, List[float]]:
        from scipy import interpolate

        original_breakpoints = self.original.deme_data[0].time_points
        original_sizes = self.original.deme_data[0].sizes
        rmses = {}
        for seq, deme_per_seq in self.deme_per_seq.items():
            for deme in deme_per_seq.deme_data:
                deme_breakpoints = deme.time_points
                deme_sizes = deme.sizes
                breakpoints_min = max(min(original_breakpoints), min(deme_breakpoints))
                breakpoints_max = min(max(original_breakpoints), max(deme_breakpoints))

                if breakpoints_min ==0:
                    breakpoints_min = 1
                common_breakpoints = np.logspace(
                    np.log10(breakpoints_min),
                    np.log10(breakpoints_max-1),
                    100)

                orig_interp = interpolate.interp1d(original_breakpoints, original_sizes, kind='nearest')(common_breakpoints)
                deme_interp = interpolate.interp1d(deme_breakpoints, deme_sizes, kind='nearest')(common_breakpoints)

                rmse = np.sqrt(np.mean((orig_interp - deme_interp) ** 2))
                if seq not in rmses:
                    rmses[seq] = []
                rmses[seq].append(rmse)
        return rmses

    def draw_sizes_per_seq(self, start_time: float, end_time: float,
                            plot_file_name: str = "deme_boxplot_plot.png"):
        """
        Plot boxplot of population sizes per sequence in a time window.

        Args:
            start_time: Start time for size calculation
            end_time: End time for size calculation
        """

        sizes_per_seq = self.sizes_in_a_time_window(start_time, end_time)
        fig, ax = plt.subplots(figsize=(10, 6))
        keys = sorted(sizes_per_seq, key=lambda k: (int(k.split('_')[0]), k.split('_')[1]))

        data, pos = [], []
        x = 1
        prev_i = None
        ticks = []
        for k in keys:
            i = int(k.split('_')[0])
            ticks.append(f"{i}\n{k.split('_')[1]}")
            if prev_i is not None and i != prev_i:
                x += 0.5          # bigger gap between different ints
            data.append(sizes_per_seq[k])
            pos.append(x)
            x += 0.3            # very small gap within same int
            prev_i = i
            
        bp = ax.boxplot(data, positions=pos, widths=0.15,
                        showfliers=False, patch_artist=True)

        # color by suffix
        suffixes = [k.split('_')[1] for k in keys]
        colors = dict(zip(sorted(set(suffixes)), plt.cm.tab10.colors))

        for box, suf in zip(bp['boxes'], suffixes):
            box.set_facecolor(colors[suf])

        ax.set_xticks(pos)
        ax.set_xticklabels(ticks)
        handles = [Patch(facecolor=colors[s], label=s) for s in sorted(colors)]
        #ax.legend(handles=handles)


        orig_sizes = self.original._get_sizes_at_interval(start_time, end_time)
        assert len(orig_sizes) == 1, "Expected exactly one size for the original deme in the interval."
        ax.axhline(y=orig_sizes[0], color='red', linestyle='--', label='Original deme size')

        ax.set_xlabel('Sequence', fontsize=12)
        ax.set_ylabel('Population Size', fontsize=12)
        ax.set_title(f'Population Sizes Across Sequences ({start_time}-{end_time} generations)', fontsize=14, fontweight='bold')
        #ax.set_yscale('log')

        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(plot_file_name)

    def draw_error_boxplots(self, plot_file_name: str = "deme_boxplot_plot.png", method: str = "frechet"):
        """
        Plot boxplot of population sizes per sequence in a time window.

        Args:

            
        """
        if method == "frechet":
            sizes_per_seq = self.frechet_dist()
            tittle = 'Fréchet Distance Between theoritical demography and Blockbuster\'s inferred demography \nfrom simulations (100 Replicates).\nThe lower the better.'
            plot_file_name = plot_file_name.replace(".png", "_frechet.png")
        elif method == "bootstrap":
            sizes_per_seq = self.error_mean_bootsrap()
            tittle = 'Fréchet Distance Between theoritical demography and the inferred Mean Demography \n Across 100 Replicates (100× Bootstrap).\nThe lower the better.'
            plot_file_name = plot_file_name.replace(".png", "_bootstrap.png")
        elif method == "rmse":
            sizes_per_seq = self.rmse()
            tittle = 'Root Mean Square Error Between theoritical demography and Blockbuster\'s inferred demography \nfrom simulations (100 Replicates).\nThe lower the better.'
            plot_file_name = plot_file_name.replace(".png", "_rmse.png")

        fig, ax = plt.subplots(figsize=(10, 6))
        keys = sorted(sizes_per_seq, key=lambda k: (int(k.split('_')[0]), k.split('_')[1]))

        data, pos = [], []
        x = 1
        prev_i = None
        ticks = []
        for k in keys:
            i = int(k.split('_')[0])
            ticks.append(f"{i}\n{k.split('_')[1]}")
            if prev_i is not None and i != prev_i:
                x += 0.5          # bigger gap between different ints
            data.append(sizes_per_seq[k])
            pos.append(x)
            x += 0.3            # very small gap within same int
            prev_i = i
            
        bp = ax.boxplot(data, positions=pos, widths=0.15,
                        showfliers=False, patch_artist=True)

        # color by suffix
        suffixes = [k.split('_')[1] for k in keys]
        colors = dict(zip(sorted(set(suffixes)), plt.cm.tab10.colors))

        for box, suf in zip(bp['boxes'], suffixes):
            box.set_facecolor(colors[suf])

        ax.set_xticks(pos)
        ax.set_xticklabels(ticks)
        handles = [Patch(facecolor=colors[s], label=s) for s in sorted(colors)]
        #ax.legend(handles=handles)

        ax.set_xlabel('Sequence', fontsize=12)
        #ax.set_ylabel('Population Size', fontsize=12)
        ax.set_title(tittle, fontsize=13, loc='left')
        #ax.set_yscale('log')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(plot_file_name)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Analyze and plot population size envelopes from demes YAML files.")
    parser.add_argument("function", type=str, nargs='?', default="envelope", 
                        choices=["envelope", "boxplot"],
                        help="Function to run: 'envelope' or 'boxplot' (default: envelope)")
    parser.add_argument("-d", type=str, help="Path to the combined demes YAML file.")
    parser.add_argument("-r", type=str, help="Path to the original deme YAML file for comparison.")
    parser.add_argument("-o", type=str, default="deme_envelope_plot.png", help="Output plot file name.")
    parser.add_argument("-s", nargs='+', type=str, default=None, help="list of successful runs")
    parser.add_argument("-p", type=str, default="", help="prefix of the file names")
    
    args = parser.parse_args()
    
    if args.function == "envelope":
        envelope = EnvelopePlotter(args.d, args.r)
        envelope.plot_envelope(plot_file_name=args.o)
    
    elif args.function == "boxplot":
        boxplot = BoxPlotter(args.s, args.r, prefix=args.p)
        #boxplot.draw_sizes_per_seq(start_time=675000, end_time=80000, plot_file_name=args.o)
        middle_epoch = boxplot.original.deme_data[0].epochs[1]
        start_time = int(float(middle_epoch["start_time"]*0.8))
        end_time = int(float(middle_epoch["end_time"]*1.2))
        boxplot.draw_sizes_per_seq(start_time=start_time, end_time=end_time, plot_file_name=args.o)

        boxplot.draw_error_boxplots(plot_file_name=args.o, method="frechet")
        boxplot.draw_error_boxplots(plot_file_name=args.o, method="rmse")
        boxplot.draw_error_boxplots(plot_file_name=args.o, method="bootstrap")
