from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QFrame, QSpacerItem, QSizePolicy)
from PyQt5.QtGui import QFont, QPainter
from PyQt5.QtCore import Qt, QTimer

# Try to import QtChart module
try:
    from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis
    HAS_CHARTS = True
except ImportError:
    HAS_CHARTS = False
    print("QtChart module not available. Charts will be disabled.")

class FocusMetricsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Check if QtChart is available
        self.has_charts = HAS_CHARTS
        
        if self.has_charts:
            # Initialize chart data
            self.focus_series = QLineSeries()
            self.focus_series.setName("Focus Time")
            self.chart_data_points = []
        
        self.initUI()
        
        # Initialize focus metrics
        self.focus_time = 0
        self.distraction_count = 0
        self.avg_distraction_time = 0
        
        if self.has_charts:
            # Setup chart update timer only if charts are available
            self.update_timer = QTimer()
            self.update_timer.timeout.connect(self.update_chart)
            self.update_timer.start(5000) # Update chart every 5 seconds
    
    def initUI(self):
        layout = QVBoxLayout()
        
        # Focus status indicator
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Focus Status:")
        self.status_label.setFont(QFont("Arial", 12, QFont.Bold))
        
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(20, 20)
        self.status_indicator.setStyleSheet("background-color: green; border-radius: 10px;")
        
        self.focus_status_text = QLabel("Focused")
        self.focus_status_text.setFont(QFont("Arial", 12))
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.status_indicator)
        status_layout.addWidget(self.focus_status_text)
        status_layout.addStretch()
        
        # Current session metrics
        metrics_frame = QFrame()
        metrics_frame.setFrameShape(QFrame.StyledPanel)
        metrics_frame.setStyleSheet("background-color: #f0f0f0; border-radius: 5px;")
        
        metrics_layout = QVBoxLayout(metrics_frame)
        metrics_layout.setSpacing(10)
        
        # Session title
        session_title = QLabel("Current Session")
        session_title.setFont(QFont("Arial", 12, QFont.Bold))
        metrics_layout.addWidget(session_title)
        
        # Focus time
        focus_time_layout = QHBoxLayout()
        focus_time_label = QLabel("Focus Time:")
        self.focus_time_value = QLabel("00:00:00")
        self.focus_time_value.setFont(QFont("Arial", 14, QFont.Bold))
        focus_time_layout.addWidget(focus_time_label)
        focus_time_layout.addWidget(self.focus_time_value)
        focus_time_layout.addStretch()
        metrics_layout.addLayout(focus_time_layout)
        
        # Distraction count
        distraction_layout = QHBoxLayout()
        distraction_label = QLabel("Distractions:")
        self.distraction_value = QLabel("0")
        self.distraction_value.setFont(QFont("Arial", 14, QFont.Bold))
        distraction_layout.addWidget(distraction_label)
        distraction_layout.addWidget(self.distraction_value)
        distraction_layout.addStretch()
        metrics_layout.addLayout(distraction_layout)
        
        # Avg distraction time
        avg_distraction_layout = QHBoxLayout()
        avg_distraction_label = QLabel("Avg. Distraction Time:")
        self.avg_distraction_value = QLabel("0.0s")
        self.avg_distraction_value.setFont(QFont("Arial", 14, QFont.Bold))
        avg_distraction_layout.addWidget(avg_distraction_label)
        avg_distraction_layout.addWidget(self.avg_distraction_value)
        avg_distraction_layout.addStretch()
        metrics_layout.addLayout(avg_distraction_layout)
        
        # Focus trend chart
        if self.has_charts:
            chart_layout = QVBoxLayout()
            chart_title = QLabel("Focus Trend")
            chart_title.setFont(QFont("Arial", 12, QFont.Bold))
            chart_layout.addWidget(chart_title)
            
            self.chart = QChart()
            self.chart.setTitle("Focus Time (last 30 minutes)")
            self.chart.addSeries(self.focus_series)
            
            self.axis_x = QValueAxis()
            self.axis_x.setRange(0, 30)
            self.axis_x.setLabelFormat("%d")
            self.axis_x.setTitleText("Time (minutes)")
            
            self.axis_y = QValueAxis()
            self.axis_y.setRange(0, 100)
            self.axis_y.setLabelFormat("%d")
            self.axis_y.setTitleText("Focus (%)")
            
            self.chart.addAxis(self.axis_x, Qt.AlignBottom)
            self.chart.addAxis(self.axis_y, Qt.AlignLeft)
            
            self.focus_series.attachAxis(self.axis_x)
            self.focus_series.attachAxis(self.axis_y)
            
            self.chart_view = QChartView(self.chart)
            self.chart_view.setRenderHint(QPainter.Antialiasing)
            self.chart_view.setMinimumHeight(200)
            
            chart_layout.addWidget(self.chart_view)
            layout.addLayout(chart_layout)
        else:
            # Alternative to chart - just a placeholder message
            chart_placeholder = QLabel("Focus trend chart unavailable - PyQtChart module not installed")
            chart_placeholder.setAlignment(Qt.AlignCenter)
            chart_placeholder.setStyleSheet("background-color: #f0f0f0; padding: 20px; border-radius: 5px;")
            chart_placeholder.setMinimumHeight(100)
            layout.addWidget(chart_placeholder)
        
        # Add all layouts to main layout
        layout.addLayout(status_layout)
        layout.addWidget(metrics_frame)
        
        self.setLayout(layout)
    
    def update_metrics(self, focus_data):
        # Update focus status indicator
        is_focused = focus_data["focused"]
        status_color = "green" if is_focused else "red"
        status_text = "Focused" if is_focused else "Distracted"
        
        self.status_indicator.setStyleSheet(f"background-color: {status_color}; border-radius: 10px;")
        self.focus_status_text.setText(status_text)
        
        # Update focus time
        focus_seconds = focus_data["focus_duration"]
        hours, remainder = divmod(focus_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.focus_time_value.setText(f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}")
        
        # Update distraction count
        self.distraction_count = focus_data["distraction_count"]
        self.distraction_value.setText(str(self.distraction_count))
        
        # Update average distraction time
        self.avg_distraction_time = focus_data["avg_distraction_time"]
        self.avg_distraction_value.setText(f"{self.avg_distraction_time:.1f}s")
        
        # Store data for chart update
        self.focus_time = focus_seconds
    
    def update_chart(self):
        # Only update chart if we have charts enabled
        if not hasattr(self, 'has_charts') or not self.has_charts:
            return
        
        # Add a new data point every 5 seconds
        # Calculate focus percentage over the last interval
        focus_percent = 100 # Default to 100% if we don't have enough data yet
        
        # Add the point to the series
        minutes_elapsed = len(self.chart_data_points) / 12 # 12 points per minute (5-second intervals)
        
        if len(self.chart_data_points) >= 360: # Keep 30 minutes of data (360 points)
            self.chart_data_points.pop(0)
        
        # Only add a data point if we have valid focus data
        if hasattr(self, 'focus_time'):
            self.chart_data_points.append(focus_percent)
        
        # Clear the series and repopulate with all data points
        self.focus_series.clear()
        
        for i, point in enumerate(self.chart_data_points):
            minute = i / 12 # Convert to minutes
            self.focus_series.append(minute, point)
        
        # Adjust X axis range to show only the last 30 minutes of data
        max_minutes = min(30, len(self.chart_data_points) / 12)
        self.axis_x.setRange(0, max_minutes)