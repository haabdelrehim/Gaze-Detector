import numpy as np
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QComboBox, QFrame, QApplication)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
import traceback
import sys

# Debug flag - set to True for verbose debugging
DEBUG = True

def debug_print(*args, **kwargs):
    if DEBUG:
        print("[EyeMovementAnalysis]", *args, **kwargs)

class MatplotlibCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=6, dpi=100):
        debug_print("Initializing MatplotlibCanvas")
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MatplotlibCanvas, self).__init__(fig)
        # Make sure background is set correctly for Qt
        fig.patch.set_facecolor('#2D2D30')
        self.axes.set_facecolor('#3E3E42')
        self.axes.tick_params(colors='white')
        for spine in self.axes.spines.values():
            spine.set_color('white')
        self.axes.set_title("Eye Movement Analysis", color='white')
        self.axes.set_xlabel("Value", color='white')
        self.axes.set_ylabel("Frequency", color='white')

class EyeMovementAnalysisWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_data = None
        debug_print("Initializing EyeMovementAnalysisWidget")
        self.initUI()
    
    def initUI(self):
        debug_print("Setting up UI")
        try:
            layout = QVBoxLayout(self)
            
            # Title
            title = QLabel("Eye Movement Analysis")
            title.setFont(QFont("Arial", 14, QFont.Bold))
            layout.addWidget(title)
            
            # Info text
            info_text = QLabel(
                "This analysis shows eye movement patterns that can be relevant to neurodivergence research.\n"
                "Saccades (rapid eye movements) and fixations (steady gaze periods) follow specific distributions."
            )
            info_text.setWordWrap(True)
            layout.addWidget(info_text)
            
            # Plot selection
            selection_layout = QHBoxLayout()
            selection_layout.addWidget(QLabel("Select plot type:"))
            
            self.plot_type_combo = QComboBox()
            self.plot_type_combo.addItems([
                "Gaze Ratio Changes (Linear)",
                "Gaze Ratio Changes (Semi-log)",
                "Gaze Ratio Changes (Log-log)",
                "Fixation Durations (Linear)",
                "Fixation Durations (Semi-log)",
                "Fixation Durations (Log-log)"
            ])
            self.plot_type_combo.currentIndexChanged.connect(self.update_plot)
            selection_layout.addWidget(self.plot_type_combo)
            
            
            
            layout.addLayout(selection_layout)
            
            # Matplotlib canvas for plotting
            debug_print("Creating MatplotlibCanvas")
            self.canvas = MatplotlibCanvas(self, width=5, height=6, dpi=100)
            layout.addWidget(self.canvas)
            
            # Status message
            self.status_label = QLabel("No data loaded yet")
            self.status_label.setStyleSheet("color: yellow;")
            layout.addWidget(self.status_label)
            
            # Interpretation frame
            interpretation_frame = QFrame()
            interpretation_frame.setFrameShape(QFrame.StyledPanel)
            interpretation_frame.setStyleSheet("background-color: #3E3E42; border-radius: 5px; padding: 10px;")
            
            interpretation_layout = QVBoxLayout(interpretation_frame)
            
            interpretation_title = QLabel("Interpretation")
            interpretation_title.setFont(QFont("Arial", 12, QFont.Bold))
            interpretation_layout.addWidget(interpretation_title)
            
            self.interpretation_text = QLabel(
                "This plot can show patterns related to neurodivergent eye movements.\n"
                "An exponential distribution (straight line in semi-log) suggests random movements.\n"
                "A power-law distribution (straight line in log-log) suggests more complex patterns."
            )
            self.interpretation_text.setWordWrap(True)
            interpretation_layout.addWidget(self.interpretation_text)
            
            layout.addWidget(interpretation_frame)
            
            # Add a clear message if no data is available yet
            self.canvas.axes.text(0.5, 0.5, "No eye movement data available yet",
                             horizontalalignment='center',
                             verticalalignment='center',
                             transform=self.canvas.axes.transAxes,
                             color='white',
                             fontsize=14)
            self.canvas.draw()
            
            debug_print("UI setup complete")
        except Exception as e:
            debug_print(f"Error in initUI: {e}")
            traceback.print_exc()
            
    def debug_info(self):
        """Display debug info about the current data"""
        if not self.current_data:
            self.status_label.setText("No data loaded!")
            self.status_label.setStyleSheet("color: red;")
            return
            
        debug_str = f"Data loaded: {type(self.current_data)}\n"
        
        for key, value in self.current_data.items():
            if isinstance(value, list):
                debug_str += f"{key}: {len(value)} items, type: {type(value)}\n"
                if value:
                    debug_str += f"  First few items: {value[:min(5, len(value))]}\n"
            else:
                debug_str += f"{key}: {value}, type: {type(value)}\n"
        
        print(debug_str)
        self.status_label.setText(f"Data summary: {len(self.current_data.get('gaze_ratio_changes', []))} gaze changes, "
                                 f"{len(self.current_data.get('fixation_durations', []))} fixations")
        self.status_label.setStyleSheet("color: lime;")
    
    def set_data(self, eye_movement_data):
        """Set the eye movement data for analysis"""
        debug_print(f"Setting data: {type(eye_movement_data)}")
        try:
            if not eye_movement_data:
                debug_print("No data provided (None or empty)")
                self.status_label.setText("No data provided!")
                self.status_label.setStyleSheet("color: red;")
                return
                
            if not isinstance(eye_movement_data, dict):
                debug_print(f"Expected dict, got {type(eye_movement_data)}")
                self.status_label.setText(f"Invalid data type: {type(eye_movement_data)}")
                self.status_label.setStyleSheet("color: red;")
                return
                
            # Check required keys
            for key in ['gaze_ratio_changes', 'fixation_durations']:
                if key not in eye_movement_data:
                    debug_print(f"Missing key: {key}")
                    self.status_label.setText(f"Missing key in data: {key}")
                    self.status_label.setStyleSheet("color: red;")
                    return
                    
            self.current_data = eye_movement_data
            debug_print(f"Data set successfully, gaze_changes: {len(eye_movement_data['gaze_ratio_changes'])}, "
                       f"fixations: {len(eye_movement_data['fixation_durations'])}")
            
            self.status_label.setText(f"Data loaded: {len(eye_movement_data['gaze_ratio_changes'])} gaze changes, "
                                     f"{len(eye_movement_data['fixation_durations'])} fixations")
            self.status_label.setStyleSheet("color: lime;")
            
            self.update_plot()
        except Exception as e:
            debug_print(f"Error in set_data: {e}")
            traceback.print_exc()
            self.status_label.setText(f"Error setting data: {str(e)}")
            self.status_label.setStyleSheet("color: red;")
    
    def update_plot(self):
        """Update the plot based on selected type"""
        debug_print("Updating plot")
        try:
            if not self.current_data:
                debug_print("No data available to plot")
                self.canvas.axes.clear()
                self.canvas.axes.text(0.5, 0.5, "No eye movement data available",
                                 horizontalalignment='center',
                                 verticalalignment='center',
                                 transform=self.canvas.axes.transAxes,
                                 color='white',
                                 fontsize=14)
                self.canvas.draw()
                return
            
            # Get the current plot type from the combo box
            plot_type = self.plot_type_combo.currentText()
            debug_print(f"Plotting: {plot_type}")
            
            self.canvas.axes.clear()
            
            # Set colors for dark theme
            self.canvas.axes.set_facecolor('#3E3E42')
            self.canvas.axes.tick_params(colors='white')
            for spine in self.canvas.axes.spines.values():
                spine.set_color('white')
            
            if "Gaze Ratio Changes" in plot_type:
                data = self.current_data.get('gaze_ratio_changes', [])
                debug_print(f"Gaze ratio changes data: {len(data)} points")
                title = "Distribution of Gaze Ratio Changes (Saccades)"
                xlabel = "Gaze Ratio Change"
                ylabel = "Frequency"
            else:  # Fixation Durations
                data = self.current_data.get('fixation_durations', [])
                debug_print(f"Fixation durations data: {len(data)} points")
                title = "Distribution of Fixation Durations"
                xlabel = "Duration (seconds)"
                ylabel = "Frequency"
            
            if not data:
                debug_print("No specific data for selected plot type")
                self.canvas.axes.text(0.5, 0.5, "No data available for this plot type",
                                 horizontalalignment='center',
                                 verticalalignment='center',
                                 transform=self.canvas.axes.transAxes,
                                 color='white',
                                 fontsize=14)
                self.canvas.draw()
                return
            
            # Convert data to numpy array for proper histogram handling
            data_array = np.array(data)
            debug_print(f"Data range: {np.min(data_array)} to {np.max(data_array)}")
            
            # Create histogram with appropriate number of bins
            num_bins = min(20, max(5, len(data) // 2))
            hist, bin_edges = np.histogram(data_array, bins=num_bins)
            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
            
            debug_print(f"Created histogram with {num_bins} bins")
            
            # Apply log transformations based on plot type
            if "Semi-log" in plot_type:
                debug_print("Using semi-log scale")
                self.canvas.axes.set_yscale('log')
                interpretation = "Exponential distribution appears as a straight line in semi-log scale.\n"
                if "Gaze Ratio Changes" in plot_type:
                    interpretation += "If the line is straight, eye movements have a characteristic scale."
                else:
                    interpretation += "If the line is straight, fixation durations follow a random process."
            elif "Log-log" in plot_type:
                debug_print("Using log-log scale")
                self.canvas.axes.set_xscale('log')
                self.canvas.axes.set_yscale('log')
                interpretation = "Power-law distribution appears as a straight line in log-log scale.\n"
                if "Gaze Ratio Changes" in plot_type:
                    interpretation += "If the line is straight, eye movements have scale-free properties."
                else:
                    interpretation += "If the line is straight, fixation durations show complex patterns."
            else:  # Linear
                debug_print("Using linear scale")
                interpretation = "Linear plot shows the raw distribution.\n"
                if "Gaze Ratio Changes" in plot_type:
                    interpretation += "Look for clusters indicating preferred saccade distances."
                else:
                    interpretation += "Look for multiple peaks indicating preferred fixation durations."
            
            # Plot the histogram with custom colors
            bars = self.canvas.axes.bar(bin_centers, hist, width=bin_edges[1] - bin_edges[0], alpha=0.7, color='#1E90FF')
            
            # Add best fit lines for analysis
            if len(data) > 5:  # Only try to fit if we have enough data points
                try:
                    debug_print("Attempting to fit curve to data")
                    # Import scipy only if needed
                    from scipy import stats
                    from scipy.optimize import curve_fit
                    
                    # For linear plots
                    if "Linear" in plot_type:
                        # Try normal distribution fit
                        mu, sigma = stats.norm.fit(data_array)
                        x = np.linspace(min(data_array), max(data_array), 100)
                        y = stats.norm.pdf(x, mu, sigma) * len(data_array) * (bin_edges[1] - bin_edges[0])
                        self.canvas.axes.plot(x, y, 'r-', linewidth=2, label=f'Normal Fit (μ={mu:.2f}, σ={sigma:.2f})')
                        self.canvas.axes.legend(facecolor='#3E3E42', edgecolor='white', labelcolor='white')
                        debug_print(f"Added normal fit: μ={mu:.2f}, σ={sigma:.2f}")
                    
                    # For semi-log plots (exponential fit)
                    elif "Semi-log" in plot_type:
                        # Fit exponential
                        def exp_func(x, a, b):
                            return a * np.exp(-b * x)
                        
                        # Filter out zeros and empty bins
                        valid_indices = hist > 0
                        if np.any(valid_indices):
                            valid_x = bin_centers[valid_indices]
                            valid_y = hist[valid_indices]
                            try:
                                popt, _ = curve_fit(exp_func, valid_x, valid_y)
                                x_fit = np.linspace(min(bin_centers), max(bin_centers), 100)
                                y_fit = exp_func(x_fit, *popt)
                                self.canvas.axes.plot(x_fit, y_fit, 'r-', linewidth=2, label=f'Exp Fit (λ={popt[1]:.4f})')
                                self.canvas.axes.legend(facecolor='#3E3E42', edgecolor='white', labelcolor='white')
                                debug_print(f"Added exponential fit: λ={popt[1]:.4f}")
                                
                                interpretation += f"\nExponential decay rate: λ={popt[1]:.4f}"
                            except Exception as e:
                                debug_print(f"Error fitting exponential: {e}")
                    
                    # For log-log plots (power-law fit)
                    elif "Log-log" in plot_type:
                        # Fit power law
                        def power_law(x, a, b):
                            return a * np.power(x, b)
                        
                        # Filter out zeros and empty bins
                        valid_indices = (hist > 0) & (bin_centers > 0)
                        if np.any(valid_indices):
                            valid_x = bin_centers[valid_indices]
                            valid_y = hist[valid_indices]
                            try:
                                popt, _ = curve_fit(power_law, valid_x, valid_y)
                                x_fit = np.linspace(min(valid_x), max(valid_x), 100)
                                y_fit = power_law(x_fit, *popt)
                                self.canvas.axes.plot(x_fit, y_fit, 'r-', linewidth=2, label=f'Power Law (α={-popt[1]:.2f})')
                                self.canvas.axes.legend(facecolor='#3E3E42', edgecolor='white', labelcolor='white')
                                debug_print(f"Added power law fit: α={-popt[1]:.2f}")
                                
                                interpretation += f"\nPower law exponent: α={-popt[1]:.2f}"
                            except Exception as e:
                                debug_print(f"Error fitting power law: {e}")
                except ImportError as e:
                    debug_print(f"SciPy import error: {e}")
                except Exception as e:
                    debug_print(f"Error during curve fitting: {e}")
            
            # Set plot properties with colors for dark theme
            self.canvas.axes.set_title(title, color='white')
            self.canvas.axes.set_xlabel(xlabel, color='white')
            self.canvas.axes.set_ylabel(ylabel, color='white')
            self.canvas.axes.grid(True, linestyle='--', alpha=0.7, color='gray')
            
            # Make sure the plot is visible
            self.canvas.draw()
            debug_print("Plot updated successfully")
            
            # Update interpretation text
            self.interpretation_text.setText(interpretation)
            
        except Exception as e:
            debug_print(f"Error updating plot: {e}")
            traceback.print_exc()
            self.canvas.axes.clear()
            self.canvas.axes.text(0.5, 0.5, f"Error plotting data:\n{str(e)}",
                             horizontalalignment='center',
                             verticalalignment='center',
                             transform=self.canvas.axes.transAxes,
                             color='red',
                             fontsize=12)
            self.canvas.draw()
            self.status_label.setText(f"Error plotting: {str(e)}")
            self.status_label.setStyleSheet("color: red;")


# Add this for standalone testing
if __name__ == "__main__":
    debug_print("Running standalone test")
    app = QApplication(sys.argv)
    
    # Create test data
    test_data = {
        'gaze_ratio_changes': [0.5, 1.2, 2.3, 1.1, 0.8, 1.5, 2.0, 1.7, 0.9, 1.3],
        'fixation_durations': [0.3, 0.5, 0.8, 0.2, 0.4, 0.6, 0.7, 0.9, 1.0, 0.5]
    }
    
    # Create widget
    widget = EyeMovementAnalysisWidget()
    widget.set_data(test_data)
    widget.show()
    
    sys.exit(app.exec_())