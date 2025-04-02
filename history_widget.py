from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QSplitter, QFrame)
from PyQt5.QtGui import QFont, QPainter
from PyQt5.QtCore import Qt, QDateTime, pyqtSignal
from datetime import datetime, timedelta

# Try to import QtChart module
try:
    from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis
    HAS_CHARTS = True
except ImportError:
    HAS_CHARTS = False
    print("QtChart module not available. Charts will be disabled in History view.")

class HistoryWidget(QWidget):
    """Widget for displaying session history and detailed session analysis"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_session_id = None
        self.has_charts = HAS_CHARTS
        
        self.initUI()
        self.refresh_sessions()
    
    def initUI(self):
        """Initialize the UI components"""
        main_layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Session History")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        main_layout.addWidget(title_label)
        
        # Create splitter for sessions list and session details
        splitter = QSplitter(Qt.Vertical)
        
        # Sessions table
        self.sessions_table = QTableWidget()
        self.sessions_table.setColumnCount(7)
        self.sessions_table.setHorizontalHeaderLabels([
            "Date", "Duration", "Distractions", 
            "Avg. Distraction", "Focus %", "Longest Focus", "Actions"
        ])
        
        # Set table properties
        self.sessions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.sessions_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.sessions_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.sessions_table.setAlternatingRowColors(True)
        self.sessions_table.setStyleSheet("""
            QTableWidget {
                background-color: #2D2D30;
                alternate-background-color: #3E3E42;
                color: #E0E0E0;
                gridline-color: #555555;
            }
            QHeaderView::section {
                background-color: #007ACC;
                color: white;
                padding: 6px;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #264F78;
            }
        """)
        
        # Connect cell clicked signal
        self.sessions_table.cellClicked.connect(self.on_session_selected)
        
        # Session details section
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        
        # Session details header
        self.details_title = QLabel("Session Details")
        self.details_title.setFont(QFont("Arial", 12, QFont.Bold))
        details_layout.addWidget(self.details_title)
        
        # Session data and chart in a horizontal layout
        data_chart_layout = QHBoxLayout()
        
        # Session metrics
        metrics_frame = QFrame()
        metrics_frame.setFrameShape(QFrame.StyledPanel)
        metrics_frame.setStyleSheet("background-color: #3E3E42; border-radius: 5px;")
        
        metrics_layout = QVBoxLayout(metrics_frame)
        
        # Session metrics labels
        self.date_label = QLabel("Date: -")
        self.duration_label = QLabel("Duration: -")
        self.distraction_count_label = QLabel("Distractions: -")
        self.avg_distraction_label = QLabel("Avg. Distraction Time: -")
        self.focus_percentage_label = QLabel("Focus Percentage: -")
        self.longest_focus_label = QLabel("Longest Focus Period: -")
        
        # Add metrics to layout
        metrics_layout.addWidget(QLabel("Session Metrics:"))
        metrics_layout.addWidget(self.date_label)
        metrics_layout.addWidget(self.duration_label)
        metrics_layout.addWidget(self.distraction_count_label)
        metrics_layout.addWidget(self.avg_distraction_label)
        metrics_layout.addWidget(self.focus_percentage_label)
        metrics_layout.addWidget(self.longest_focus_label)
        metrics_layout.addStretch()
        
        # Focus chart
        chart_frame = QFrame()
        chart_frame.setFrameShape(QFrame.StyledPanel)
        chart_frame.setStyleSheet("background-color: #3E3E42; border-radius: 5px;")
        
        chart_layout = QVBoxLayout(chart_frame)
        chart_layout.addWidget(QLabel("Focus Timeline:"))
        
        if self.has_charts:
            # Create chart
            self.chart = QChart()
            self.chart.setTitle("Focus Over Time")
            self.chart.setAnimationOptions(QChart.SeriesAnimations)
            
            # Create chart view
            self.chart_view = QChartView(self.chart)
            self.chart_view.setRenderHint(QPainter.Antialiasing)
            self.chart_view.setMinimumHeight(200)
            
            chart_layout.addWidget(self.chart_view)
        else:
            # Show placeholder if charts are not available
            chart_placeholder = QLabel("Focus charts not available (PyQtChart module not installed)")
            chart_placeholder.setAlignment(Qt.AlignCenter)
            chart_placeholder.setStyleSheet("padding: 40px; color: #E0E0E0;")
            chart_layout.addWidget(chart_placeholder)
        
        # Add metrics and chart to horizontal layout
        data_chart_layout.addWidget(metrics_frame, 1)
        data_chart_layout.addWidget(chart_frame, 3)
        
        details_layout.addLayout(data_chart_layout)
        
        # Add widgets to splitter and set initial sizes
        splitter.addWidget(self.sessions_table)
        splitter.addWidget(details_widget)
        splitter.setSizes([200, 300])
        
        main_layout.addWidget(splitter)
        
        # Refresh button
        refresh_button = QPushButton("Refresh Sessions")
        refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #007ACC;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #005999;
            }
        """)
        refresh_button.clicked.connect(self.refresh_sessions)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(refresh_button)
        
        main_layout.addLayout(button_layout)
    
    def refresh_sessions(self):
        """Load and display all sessions from the database"""
        # Clear existing rows
        self.sessions_table.setRowCount(0)
        
        # Get all sessions from database
        sessions = self.db_manager.get_all_sessions()
        
        # Populate table
        for i, session in enumerate(sessions):
            self.sessions_table.insertRow(i)
            
            # Format and add session data to table
            date_str = session['start_time'].strftime("%Y-%m-%d %H:%M:%S")
            self.sessions_table.setItem(i, 0, QTableWidgetItem(date_str))
            
            # Format duration (HH:MM:SS)
            hours, remainder = divmod(session['duration'], 3600)
            minutes, seconds = divmod(remainder, 60)
            duration_str = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
            self.sessions_table.setItem(i, 1, QTableWidgetItem(duration_str))
            
            # Distractions count
            self.sessions_table.setItem(i, 2, QTableWidgetItem(str(session['distraction_count'])))
            
            # Average distraction time
            avg_distraction_str = f"{session['avg_distraction_time']:.1f}s"
            self.sessions_table.setItem(i, 3, QTableWidgetItem(avg_distraction_str))
            
            # Focus percentage
            focus_pct_str = f"{session['focus_percentage']:.1f}%"
            self.sessions_table.setItem(i, 4, QTableWidgetItem(focus_pct_str))
            
            # Longest focus period
            longest_focus_mins, longest_focus_secs = divmod(session['longest_focus_period'], 60)
            longest_focus_str = f"{int(longest_focus_mins)}m {int(longest_focus_secs)}s"
            self.sessions_table.setItem(i, 5, QTableWidgetItem(longest_focus_str))
            
            # View details button
            view_button = QPushButton("View")
            view_button.setStyleSheet("""
                QPushButton {
                    background-color: #007ACC;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    padding: 3px 8px;
                }
                QPushButton:hover {
                    background-color: #005999;
                }
            """)
            
            # Connect button to load session details with this session's ID
            session_id = session['id']
            view_button.clicked.connect(lambda checked, sid=session_id: self.load_session_details(sid))
            
            self.sessions_table.setCellWidget(i, 6, view_button)
    
    def on_session_selected(self, row, column):
        """Handle when a session row is clicked"""
        # Skip action column (view button)
        if column == 6:
            return
        
        # Get session ID from the first column (date)
        date_text = self.sessions_table.item(row, 0).text()
        
        # Find matching session
        sessions = self.db_manager.get_all_sessions()
        for session in sessions:
            if session['start_time'].strftime("%Y-%m-%d %H:%M:%S") == date_text:
                self.load_session_details(session['id'])
                break
    
    def load_session_details(self, session_id):
        """Load and display details for the selected session"""
        if session_id == self.current_session_id:
            return  # Already loaded
        
        # Get detailed session data
        session = self.db_manager.get_session_details(session_id)
        if not session:
            return
        
        self.current_session_id = session_id
        
        # Update session details header
        self.details_title.setText(f"Session Details - {session['start_time'].strftime('%Y-%m-%d %H:%M')}")
        
        # Update metrics
        self.date_label.setText(f"Date: {session['start_time'].strftime('%Y-%m-%d %H:%M')} - {session['end_time'].strftime('%H:%M')}")
        
        hours, remainder = divmod(session['duration'], 3600)
        minutes, seconds = divmod(remainder, 60)
        self.duration_label.setText(f"Duration: {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}")
        
        self.distraction_count_label.setText(f"Distractions: {session['distraction_count']}")
        self.avg_distraction_label.setText(f"Avg. Distraction Time: {session['avg_distraction_time']:.1f}s")
        self.focus_percentage_label.setText(f"Focus Percentage: {session['focus_percentage']:.1f}%")
        
        longest_focus_mins, longest_focus_secs = divmod(session['longest_focus_period'], 60)
        self.longest_focus_label.setText(f"Longest Focus Period: {int(longest_focus_mins)}m {int(longest_focus_secs)}s")
        
        # Update chart if available
        if self.has_charts and 'focus_points' in session and session['focus_points']:
            self.update_chart(session)
    
    def update_chart(self, session):
        """Update the focus timeline chart with session data"""
        # Clear existing chart
        self.chart.removeAllSeries()
        
        # Create focus series
        focus_series = QLineSeries()
        focus_series.setName("Focus")
        
        # Add data points from focus points
        start_time = session['start_time']
        
        for point in session['focus_points']:
            # Convert time to seconds from start
            time_delta = (point['timestamp'] - start_time).total_seconds()
            # Use 1 for focused, 0 for unfocused
            focus_value = 1 if point['is_focused'] else 0
            focus_series.append(time_delta, focus_value)
        
        # Add series to chart
        self.chart.addSeries(focus_series)
        
        # Set up axes
        axis_x = QValueAxis()
        axis_x.setRange(0, session['duration'])
        axis_x.setTickCount(10)
        axis_x.setTitleText("Time (seconds)")
        
        axis_y = QValueAxis()
        axis_y.setRange(0, 1)
        axis_y.setTickCount(2)
        axis_y.setLabelFormat("%d")
        axis_y.setTitleText("Focus State")
        
        self.chart.addAxis(axis_x, Qt.AlignBottom)
        self.chart.addAxis(axis_y, Qt.AlignLeft)
        
        focus_series.attachAxis(axis_x)
        focus_series.attachAxis(axis_y)