import yaml
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Dict, Tuple
import argparse
import os 
from matplotlib.patches import Patch
import similaritymeasures # pip install similaritymeasures
import pandas as pd
from matplotlib import colormaps as mcm
from scipy.optimize import curve_fit
from scipy.stats import linregress
from typing import List, Optional

    
COLORS = mcm["Pastel1"].colors

def exponential_decay(x, a, b, c):
    """Exponential decay: y = a * exp(-b * x) + c"""
    return a * np.exp(-b * x) + c

def power_law(x, a, b, c):
    """Power law: y = a * x^(-b) + c"""
    return a * np.power(x, -b) + c

def logarithmic(x, a, b):
    """Logarithmic: y = a * log(x) + b"""
    return a * np.log(x) + b

def linear(x, a, b):
    """Linear: y = a * x + b"""
    return a * x + b

def sqrt(x, a, b):
    """Square root: y = a * x^(1/2) + b"""
    return a * np.sqrt(x) + b

def fit_models(x_data, y_data):
    """Fit different models and return the best one based on R²"""
    models = {}
    
    # Exponential decay
    try:
        popt, _ = curve_fit(exponential_decay, x_data, y_data, maxfev=10000)
        y_pred = exponential_decay(x_data, *popt)
        r2 = 1 - np.sum((y_data - y_pred)**2) / np.sum((y_data - np.mean(y_data))**2)
        models['exponential'] = {'params': popt, 'r2': r2, 'func': exponential_decay, 'name': 'Exponential'}
    except:
        pass
    
    # Power law
    try:
        popt, _ = curve_fit(power_law, x_data, y_data, maxfev=10000)
        y_pred = power_law(x_data, *popt)
        r2 = 1 - np.sum((y_data - y_pred)**2) / np.sum((y_data - np.mean(y_data))**2)
        models['power'] = {'params': popt, 'r2': r2, 'func': power_law, 'name': 'Power Law'}
    except:
        pass
    
    # Logarithmic
    try:
        popt, _ = curve_fit(logarithmic, x_data, y_data, maxfev=10000)
        y_pred = logarithmic(x_data, *popt)
        r2 = 1 - np.sum((y_data - y_pred)**2) / np.sum((y_data - np.mean(y_data))**2)
        models['logarithmic'] = {'params': popt, 'r2': r2, 'func': logarithmic, 'name': 'Logarithmic'}
    except:
        pass
    
    # Linear
    try:
        slope, intercept, r_value, _, _ = linregress(x_data, y_data)
        r2 = r_value**2
        models['linear'] = {'params': [slope, intercept], 'r2': r2, 'func': linear, 'name': 'Linear'}
    except:
        pass

    # Square root
    try:
        popt, _ = curve_fit(sqrt, x_data, y_data, maxfev=10000)
        y_pred = sqrt(x_data, *popt)
        r2 = 1 - np.sum((y_data - y_pred)**2) / np.sum((y_data - np.mean(y_data))**2)
        models['sqrt'] = {'params': popt, 'r2': r2, 'func': sqrt, 'name': 'Square Root'}
    except:
        print("Square root fit failed, likely due to negative or zero x values.")   
        pass

    
    # Find best model
    if models:
        best_model_name = max(models, key=lambda k: models[k]['r2'])
        return models, best_model_name
    return None, None

def format_si(value):
    value = float(value)
    prefixes = {
        -12: "p",
        -9:  "n",
        -6:  "µ",
        -3:  "m",
        0:  "",
        3:  "k",
        6:  "M",
        9:  "G",
        12:  "T",
    }

    if value == 0:
        return "0"

    import math
    exp = int(math.floor(math.log10(abs(value)) / 3) * 3)
    exp = max(min(exp, 12), -12)
    expressed_value = f"{value / 10**exp:.1f}".replace('.0', '')
    return f"{expressed_value}{prefixes[exp]}"

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
        self.min_time = min_time
        self.max_time = max_time
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
        if "metadata" in self.data and "earliest_time" in self.data["metadata"]:
            time_points.add(self.data["metadata"]["earliest_time"])
        else:
            last_point = self.max_time if self.max_time != float('inf') else max(time_points)*3
            time_points.add(last_point)
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
        self.prefix = prefix
        self.deme_per_seq = {s: DemesAnalyzer(f"{self.get_directory(s)}/results.yml", min_time=self.min_time, max_time=self.max_time) for s in successful_runs}        
   
    def get_directory(self, run: str) -> str:
        """
        gets the working directory of a run
        """
        return f"{self.prefix}_seq_{run}"

    def mean_errors_between_time_points_legacy(self,  start_time: float, end_time: float,
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

    def normalised_mean_errors_between_time_points(self,  start_time: float, end_time: float) -> Dict[str, List[float]]:
        """
        Calculate MSE errors between the demes of this demes analyzer and the original deme,
        between specified time points.
        Args:
            start_time: Start time for MSE calculation
            end_time: End time for MSE calculation
        Returns:
            List of MSE errors for each deme
        
        """
        errors_per_seq = {}

        for seq, deme_per_seq in self.deme_per_seq.items():
            errors_per_seq[seq] = []
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
                error = np.sqrt(np.mean((scaled_size - orig_size) ** 2))/orig_size
                errors_per_seq[seq].append(error)
        
        return errors_per_seq  

    def sizes_in_a_time_window(self,  start_time: float, end_time: float, normalise=False) -> Dict[str, List[float]]:
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
                if normalise:
                    scaled_size = scaled_size / orig_size
                sizes_per_seq[seq].append(scaled_size)
        
        return sizes_per_seq  

    def nrmse(self) -> Dict[str, List[float]]:
        from scipy import interpolate

        original_breakpoints = self.original.deme_data[0].time_points
        original_sizes = self.original.deme_data[0].sizes
        normalization_factor = np.max(original_sizes) - np.min(original_sizes)

        nrmses = {}
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
                nrmse = rmse / normalization_factor if normalization_factor != 0 else 0

                if seq not in nrmses:
                    nrmses[seq] = []
                nrmses[seq].append(nrmse)
        return nrmses

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
        elif method == "nrmse":
            sizes_per_seq = self.nrmse()
            tittle = 'Normalised Root Mean Square Error'
            plot_file_name = plot_file_name.replace(".png", "_rmse.png")

        fig, ax = plt.subplots(figsize=(10, 6))
        keys = sorted(sizes_per_seq, key=lambda k: (int(k.split('_')[0]), k.split('_')[1]))

        data, pos = [], []
        x = 1
        prev_i = None
        ticks = []
        for k in keys:
            i = int(k.split('_')[0])
            #ticks.append(f"{i}\n{k.split('_')[1]}")
            ticks.append(f"{format_si(i)}b")
            
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
        ax.tick_params(labelsize=16)


        handles = [Patch(facecolor=colors[s], label=s) for s in sorted(colors)]
        #ax.legend(handles=handles)

        #ax.set_xlabel('Sequence', fontsize=12)
        #ax.set_ylabel('Population Size', fontsize=12)
        ax.set_title(tittle, fontsize=18, loc='left')
        #ax.set_yscale('log')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(plot_file_name)

    def export_data(self, output_file: str = "boxplot_data"):
        #Data for box plot
        for i, epoch in enumerate(reversed(self.original.deme_data[0].epochs)):
            
            start_time = float(epoch["start_time"])
            end_time = int(float(epoch["end_time"]))
            if start_time == float('inf'):
                start_time = self.original.time_points[0]*1.5          
            sizes_per_seq = pd.DataFrame(self.normalised_mean_errors_between_time_points(start_time, end_time))
            sizes_per_seq.to_csv(f"{output_file}_nme_epoch{i}.csv", index=False)      

        #Data for sleeve
        largest = max(
            self.successful_runs,
            key=lambda s: (int(s.split('_')[-2].replace("k", "")), int(s.split('_')[-3]))
        )        
        combined_simulations = self.deme_per_seq[largest]

        times, means, lower, upper = combined_simulations.get_envelope_data(2.5, 97.5)
        orig_times, orig_means, _, _ =self.original.get_envelope_data(0, 100)

        df = pd.DataFrame({
            "time": times,
            "mean": means,
            "lower": lower,
            "upper": upper
        })
        
        df.to_hdf(f"{output_file}_sleeve.h5", key="processed", mode="w")
        pd.DataFrame({
            "time": orig_times,
            "mean": orig_means
        }).to_hdf(f"{output_file}_sleeve.h5", key="original")      


def plot_boxes(epochs: List[pd.DataFrame], ax: Optional[plt.Axes] = None):
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))

    # Get all runs
    runs = sorted(epochs[0].columns, key=lambda k: (int(k.split('_')[0]), int(k.split('_')[1].strip("k"))))
    ks = len(set(r.split('_')[1] for r in runs))!=1
    print(set(r.split('_')[1] for r in runs))
    num_epochs = len(epochs)
    num_runs = len(runs)
    
    # Prepare data for box plots
    positions = []
    data_to_plot = []
    box_colors = []
    
    group_width = num_epochs
    gap = 1.5
    
    for run_idx, run in enumerate(runs):
        for epoch_idx, epoch in enumerate(epochs):
            pos = run_idx * (group_width + gap) + epoch_idx
            positions.append(pos)
            data_to_plot.append(epoch[run].dropna())
            box_colors.append(COLORS[epoch_idx % len(COLORS)])
    
    # Create box plots
    bp = ax.boxplot(data_to_plot, positions=positions, widths=0.6, patch_artist=True, showfliers=False)
    
    # Color the boxes
    for patch, color in zip(bp['boxes'], box_colors):
        patch.set(facecolor=color, alpha=0.85)
    
    # Set x-axis ticks
    tick_positions = [run_idx * (group_width + gap) + (num_epochs - 1) / 2 for run_idx in range(num_runs)]
    ax.set_xticks(tick_positions)
    if not ks:
        runs_formatted = [format_si(r.split('_')[0])+"bp" for r in runs]
        ax.set_xlabel('Sequence length', fontsize=12)
    else:
        runs_formatted = ["SMC(" + format_si(r.split('_')[1].strip("k"))+")" for r in runs]
    ax.set_xticklabels(runs_formatted)
    
    # Create legend
    legend_elements = [plt.Rectangle((0, 0), 1, 1, facecolor=COLORS[i % len(COLORS)], 
                                     label=f'Epoch {i+1}') 
                       for i in range(num_epochs)]
    ax.legend(handles=legend_elements, loc='best')

    ax.set_title('Normalised Mean Squared Error')
    ax.grid(True, alpha=0.3)

    return ax

def plot_sleeve(hdf5file: str, ax: Optional[plt.Axes] = None):

    df_processed = pd.read_hdf(hdf5file, key="processed")
    df_original = pd.read_hdf(hdf5file, key="original")

    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))

    orig_times, orig_means = df_original["time"], df_original["mean"]

    sorted_times = sorted(orig_times)
    i = 0
    while i < len(orig_times)-1:
        color = COLORS[i//2 % len(COLORS)]
        t_start = sorted_times[i]
        t_end = sorted_times[i+1]
        inner_df = df_processed[(df_processed["time"] >= t_start) & (df_processed["time"] <= t_end)]
        times, means, lower, upper = inner_df["time"], inner_df["mean"], inner_df["lower"], inner_df["upper"]
        ax.fill_between(times, lower, upper, alpha=0.85, color=color)
        ax.plot(times, means, linestyle="--", color="grey", linewidth=2)
        i += 2
    ax.plot(orig_times, orig_means, color='blue', linewidth=2, label='Original deme')
    ax.set_xlabel('Time (generations)', fontsize=12)
    ax.set_title('Population Size')
    ax.set_xscale('log')
    #ax.set_title('Population Size Envelope Across Demes', fontsize=14, fontweight='bold')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    return ax

def plot_error_decay_analysis(epochs: List[pd.DataFrame], plot_file_name: str = "decay_analysis.png"):
        
    runs = sorted(epochs[0].columns, key=lambda k: (int(k.split('_')[0]), k.split('_')[1]))
    
    num_epochs = len(epochs)
    num_runs = len(runs)
    
    fig, ax = plt.subplots(figsize=(10, 6))

    middle_epoch_idx = 1# num_epochs // 2
    middle_epoch = epochs[middle_epoch_idx]
    
    run_sizes = [int(r.split('_')[0]) for r in runs]
    
    # Prepare data for inset boxplot
    inset_data = []
    inset_positions = []
    median_values = []
    
    for run_idx, run in enumerate(runs):
        inset_data.append(middle_epoch[run].dropna())
        inset_positions.append(run_sizes[run_idx])
        median_values.append(middle_epoch[run].median())
    
    # Create boxplots in inset with same color as middle epoch
    middle_epoch_color = COLORS[middle_epoch_idx % len(COLORS)]
    bp_inset = ax.boxplot(inset_data, positions=inset_positions, widths=run_sizes[0]*0.35, 
                                  patch_artist=True, showfliers=False)
    
    # Color the inset boxes with the same color as middle epoch
    for patch in bp_inset['boxes']:
        patch.set_facecolor(middle_epoch_color)
    
    # Fit models on median values
    x_data = np.array(run_sizes)
    y_data = np.array(median_values)
    
    models, best_model_name = fit_models(x_data, y_data)
    
    # Plot fitted curve
    x_smooth = np.linspace(x_data.min(), x_data.max(), 200)
    
    if models and best_model_name:
        best_model = models[best_model_name]
        y_fit = best_model['func'](x_smooth, *best_model['params'])
        ax.plot(x_smooth, y_fit, 'r-', linewidth=2, 
                     label=f"{best_model['name']} (R²={best_model['r2']:.4f})", zorder=2)
        
        # Print all model results
        print(f"\n=== Model Fitting Results for Epoch {middle_epoch_idx + 1} ===")
        for model_name, model_info in sorted(models.items(), key=lambda x: x[1]['r2'], reverse=True):
            print(f"{model_info['name']}: R² = {model_info['r2']:.6f}")
        print(f"Best model: {best_model['name']}")
    
    ax.set_xlabel('Run Size (bp)')
    ax.set_ylabel('RMSE')
    ax.set_title(f'Epoch {middle_epoch_idx + 1} - Decay Analysis', loc='left', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    ax.set_xticks(run_sizes, [format_si(s)+"bp" for s in run_sizes])

    plt.tight_layout()
    plt.savefig(plot_file_name, dpi=300, bbox_inches='tight')

def plot_an_epoch_boxes(epoch: pd.DataFrame, ax: Optional[plt.Axes] = None, epoch_idx: int = 1):
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))

    # Get all runs
    runs = sorted(epoch.columns, key=lambda k: (int(k.split('_')[0]), int(k.split('_')[1].strip("k"))))
    ks = len(set(r.split('_')[1] for r in runs))!=1
    print(set(r.split('_')[1] for r in runs))
    num_epochs = 1
    num_runs = len(runs)
    
    # Prepare data for box plots
    positions = []
    data_to_plot = []
    box_colors = []
    
    group_width = 0.5
    
    for run_idx, run in enumerate(runs):
        pos = run_idx * (group_width)
        positions.append(pos)
        data_to_plot.append(epoch[run].dropna())
        box_colors.append(COLORS[epoch_idx % len(COLORS)])
    
    # Create box plots
    bp = ax.boxplot(data_to_plot, positions=positions, widths=0.6, patch_artist=True, showfliers=False)
    
    # Color the boxes
    for patch, color in zip(bp['boxes'], box_colors):
        patch.set(facecolor=color, alpha=0.5)
    
    # Set x-axis ticks
    tick_positions = [run_idx * (group_width) + (num_epochs - 1) / 2 for run_idx in range(num_runs)]
    ax.set_xticks(tick_positions)
    if not ks:
        runs_formatted = [format_si(r.split('_')[0])+"bp" for r in runs]
        ax.set_xlabel('Sequence length', fontsize=12)
    else:
        runs_formatted = ["SMC(" + format_si(r.split('_')[1].strip("k"))+")" for r in runs]

    ax.set_xticklabels(runs_formatted)
    
    # Create legend
    legend_elements = [plt.Rectangle((0, 0), 1, 1, facecolor=COLORS[epoch_idx % len(COLORS)], 
                                     label=f'Epoch {i+1}') 
                       for i in range(num_epochs)]
    ax.legend(handles=legend_elements, loc='best')

    ax.set_title('Normalised Mean Squared Error')
    ax.grid(True, alpha=0.3)

    return ax


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Analyze and plot population size envelopes from demes YAML files.")
    parser.add_argument("function", type=str, nargs='?', default="envelope", 
                        choices=["envelope", "boxplot", "exportdata", "draw"],
                        help="Function to run: 'envelope' or 'boxplot' (default: envelope)")
    parser.add_argument("-d", type=str, help="Path to the combined demes YAML file.")
    parser.add_argument("-r", type=str, help="Path to the original deme YAML file for comparison.")
    parser.add_argument("-o", type=str, default="output", help="Output plot file name.")
    parser.add_argument("-s", nargs='+', type=str, default=None, help="list of successful runs")
    parser.add_argument("-p", type=str, default="", help="prefix of the file names")
    
    args = parser.parse_args()

    if args.function == "exportdata":

        boxplot = BoxPlotter(args.s, args.r, prefix=args.p)
        boxplot.export_data(output_file=args.o)

    elif args.function == "draw":
        output_name = args.o.replace(".png", "")
        dfs = [pd.read_csv(f"{args.o}_nme_epoch{i}.csv") for i in range(3)]

        fig, ax = plt.subplots(figsize=(10, 6))

        plot_an_epoch_boxes(dfs[1], ax=ax)
        plt.savefig(f"{output_name}_compare_boxes.png", dpi=300, bbox_inches='tight')

        plot_error_decay_analysis(dfs, plot_file_name=f"{args.o}_decay.png")
        
        fig, (ax1, ax2) = plt.subplots(
            nrows=1,
            ncols=2,
            figsize=(20, 6),
            constrained_layout=True
        )
        plot_sleeve(f"{args.o}_sleeve.h5", ax=ax1)
        plot_boxes(dfs, ax=ax2)

        plt.savefig(f"{output_name}_combinedplot.png", dpi=300, bbox_inches='tight')

