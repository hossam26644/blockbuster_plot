import yaml
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Dict, Tuple


class DemesAnalyzer:
    """Analyze and visualize population size envelopes from demes YAML files."""
    
    def __init__(self, demes_file):
        """
        Initialize with a demes file.
        
        Args:
            demes_file: Path to YAML file or YAML string
        """
        self.data = self._load_yaml(demes_file)
        self.deme_data = self._parse_demes()
        self.time_points = self._extract_time_points()
    
    def _load_yaml(self, demes_file) -> Dict:
        """Load YAML from file or string."""
        if isinstance(demes_file, str) and '\n' in demes_file:
            return yaml.safe_load(demes_file)
        else:
            with open(demes_file, 'r') as f:
                return yaml.safe_load(f)
    
    def _parse_demes(self) -> List[Dict]:
        """Parse deme epochs into a structured format."""
        deme_data = []
        
        for deme in self.data['demes']:
            epochs = []
            prev_time = float('inf')
            
            for epoch in deme['epochs']:
                end_time = epoch['end_time']
                start_size = epoch['start_size']
                
                epochs.append({
                    'start_time': prev_time,
                    'end_time': end_time,
                    'size': start_size
                })
                prev_time = end_time
            
            deme_data.append({'name': deme['name'], 'epochs': epochs})
        
        return deme_data
    
    def _extract_time_points(self) -> List[float]:
        """Extract all unique time points and sort them."""
        time_points = set()
        
        for deme in self.deme_data:
            for epoch in deme['epochs']:
                if epoch['end_time'] != float('inf'):
                    time_points.add(epoch['end_time'])
                if epoch['start_time'] != float('inf'):
                    time_points.add(epoch['start_time'])
        time_points.add(max(time_points)*1.25)
        return sorted([t for t in time_points if t != float('inf')], reverse=True)
    
    def _get_sizes_at_interval(self, t_start: float, t_end: float) -> List[float]:
        """Get population sizes for all demes in a time interval."""
        sizes = []
        
        for deme in self.deme_data:
            for epoch in deme['epochs']:
                if epoch['start_time'] >= t_start and epoch['end_time'] <= t_end:
                    sizes.append(epoch['size'])
                    break
        
        return sizes
    
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
            interval_width = t_start - t_end
            
            sizes = self._get_sizes_at_interval(t_start, t_end)
            
            if sizes:
                p_upper = np.percentile(sizes, upper_percentile)
                p_lower = np.percentile(sizes, lower_percentile)
                height = p_upper - p_lower
                area = interval_width * height
                total_area += area
                
                """print(f"Time [{t_end:.2f}, {t_start:.2f}]: "
                      f"p{lower_percentile}={p_lower:.2f}, "
                      f"p{upper_percentile}={p_upper:.2f}, "
                      f"area={area:.2f}")"""
        
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
    
    def plot_envelope(self, lower_percentile: float = 2.5,
                     upper_percentile: float = 97.5,
                     figsize: Tuple[int, int] = (10, 6),
                     original_deme_file: str = None):
        """
        Plot population size with percentile envelope.
        
        Args:
            lower_percentile: Lower percentile boundary (default 2.5)
            upper_percentile: Upper percentile boundary (default 97.5)
            figsize: Figure size as (width, height)
        """

        times, means, lower, upper = self.get_envelope_data(
            lower_percentile, upper_percentile
        )
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # Plot envelope (gray shaded region)
        ax.fill_between(times, lower, upper, alpha=0.3, color='gray', 
                        label=f'{lower_percentile}th-{upper_percentile}th percentile')

        if original_deme_file:
            original_analyzer = DemesAnalyzer(original_deme_file)
            orig_times, orig_means, _, _ = original_analyzer.get_envelope_data(0, 100)
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
        return fig, ax


# Example usage
if __name__ == "__main__":
    
    # Create analyzer
    analyzer = DemesAnalyzer("box_plot_figure/combined_demes_seq_1000/results.yml")
    
    # Calculate area
    total_area = analyzer.calculate_envelope_area()
    print(f"\nTotal area: {total_area:.2f}")
    
    # Plot envelope
    analyzer.plot_envelope(original_deme_file="/home/hossam26644/Documents/blockbuster_plot/box_plot_figure/predict_one_set/demes/DroMel_OOF_modified.yml")
    plt.show()