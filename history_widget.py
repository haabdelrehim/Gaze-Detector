from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QSplitter, QFrame, QComboBox)
from PyQt5.QtGui import QFont, QPainter
from PyQt5.QtCore import Qt, QDateTime, pyqtSignal
from datetime import datetime, timedelta
import sys
import traceback

# Try to import QtChart module
try:
    from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis
    HAS_CHARTS = True
except ImportError:
    HAS_CHARTS = False
    print("QtChart module not available. Charts will be disabled in History view.")

# Import the eye movement analysis widget directly
# Comment out the hardcoded path
# sys.path.append("Users/haabdelrehim/desktop/seperated_project/eye_movement_analysis.py")
from eye_movement_analysis import EyeMovementAnalysisWidget, debug_print

class HistoryWidget(QWidget):
    """Widget for displaying session history and detailed session analysis"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_session_id = None
        self.has_charts = HAS_CHARTS
        self.metrics_frame = None # Will be set in initUI
        self.chart_frame = None # Will be set in initUI
        self.original_height = None  # To store original height before expansion
        
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
        self.metrics_frame = QFrame()
        self.metrics_frame.setFrameShape(QFrame.StyledPanel)
        self.metrics_frame.setStyleSheet("background-color: #3E3E42; border-radius: 5px;")
        
        metrics_layout = QVBoxLayout(self.metrics_frame)
        
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
        self.chart_frame = QFrame()
        self.chart_frame.setFrameShape(QFrame.StyledPanel)
        self.chart_frame.setStyleSheet("background-color: #3E3E42; border-radius: 5px;")
        
        chart_layout = QVBoxLayout(self.chart_frame)
        chart_layout.addWidget(QLabel("Focus Timeline:"))
        
        if self.has_charts:
            # Create chart
            self.chart = QChart()
            self.chart.setTitle("Focus Over Time")
            self.chart.setAnimationOptions(QChart.SeriesAnimations)
            
            # Create chart view
            self.chart_view = QChartView(self.chart)
            self.chart_view.setRenderHint(QPainter.Antialiasing)
            self.chart_view.setMinimumHeight(300)
            
            chart_layout.addWidget(self.chart_view)
        else:
            # Show placeholder if charts are not available
            chart_placeholder = QLabel("Focus charts not available (PyQtChart module not installed)")
            chart_placeholder.setAlignment(Qt.AlignCenter)
            chart_placeholder.setStyleSheet("padding: 40px; color: #E0E0E0;")
            chart_layout.addWidget(chart_placeholder)
        
        # Add metrics and chart to horizontal layout
        data_chart_layout.addWidget(self.metrics_frame, 1)
        data_chart_layout.addWidget(self.chart_frame, 3)
        
        details_layout.addLayout(data_chart_layout)
        
        # Eye movement analysis container
        self.eye_movement_container = QWidget()
        self.eye_movement_container.setVisible(False)  # Initially hidden
        eye_movement_layout = QVBoxLayout(self.eye_movement_container)
        
        # Add status label for debugging
        self.eye_movement_status = QLabel("Eye Movement Analysis Status: Not loaded")
        eye_movement_layout.addWidget(self.eye_movement_status)
        
        # Create eye movement widget
        try:
            self.eye_movement_widget = EyeMovementAnalysisWidget()
            eye_movement_layout.addWidget(self.eye_movement_widget)
            print("Successfully created EyeMovementAnalysisWidget")
        except Exception as e:
            print(f"Error creating EyeMovementAnalysisWidget: {e}")
            traceback.print_exc()
            err_label = QLabel(f"Error loading eye movement analysis: {str(e)}")
            err_label.setStyleSheet("color: red;")
            eye_movement_layout.addWidget(err_label)
        
        # Back button to return to focus data
        back_btn = QPushButton("Back to Focus Data")
        back_btn.setStyleSheet("""
        QPushButton {
            background-color: #0078D7;
            color: white;
            padding: 6px 12px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #0063B1;
        }
        """)
        back_btn.clicked.connect(self.show_focus_data)
        eye_movement_layout.addWidget(back_btn)
        details_layout.addWidget(self.eye_movement_container)
        
        # Add widgets to splitter and set initial sizes
        splitter.addWidget(self.sessions_table)
        splitter.addWidget(details_widget)
        splitter.setSizes([180, 320])
        
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
            
            # Action dropdown
            session_id = session['id']  # Get the session ID
            
            view_widget = QWidget()
            view_layout = QVBoxLayout(view_widget)
            view_layout.setContentsMargins(2, 2, 2, 2)

            action_combo = QComboBox()
            action_combo.addItem("View Graphs")
            action_combo.addItem("View Focus Data")
            action_combo.addItem("View Eye Movement")
            action_combo.setStyleSheet("""
                QComboBox {
                    background-color: #0078D7;
                    color: white;
                    padding: 4px;
                    min-height: 25px;
                    border-radius: 3px;
                }
                QComboBox::drop-down {
                    border: none;
                }
                QComboBox QAbstractItemView {
                    background-color: #2D2D30;
                    color: white;
                    selection-background-color: #007ACC;
                }
            """)

            # Store the session ID for use in the handler
            action_combo.setProperty("session_id", session_id)
            action_combo.currentIndexChanged.connect(self.handle_action_selection)
            view_layout.addWidget(action_combo)

            self.sessions_table.setCellWidget(i, 6, view_widget)
    
    def handle_action_selection(self, index):
        """Handle action selection from the combo box"""
        # Get the combo box that sent the signal
        combo = self.sender()
        if combo and index > 0:  # Skip the "Select Action..." item
            session_id = combo.property("session_id")
            if index == 1:  # View Focus Data
                self.load_session_details(session_id)
            elif index == 2:  # View Eye Movement
                self.show_eye_analysis(session_id)
            combo.setCurrentIndex(0)  # Reset to "Select Action..."
    
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
        
        # Make sure we're showing focus data, not eye movement analysis
        self.show_focus_data()
        
        # Check if there's eye movement data and directly show it for debugging
        # Uncomment this for automatic switching to eye movement analysis
        # if 'eye_movement_data' in session and session['eye_movement_data']:
        #     self.show_eye_analysis(session_id)
    
    def update_chart(self, session):
        """Update the focus timeline chart with session data"""
        # Completely clear the existing chart
        self.chart.removeAllSeries()
        
        # Detach any existing axes
        for axis in self.chart.axes():
            self.chart.removeAxis(axis)
        
        # Create a fresh focus series
        focus_series = QLineSeries()
        focus_series.setName("Focus")
        
        # Add data points from focus points
        start_time = session['start_time']
        
        # Make sure points are sorted by timestamp
        sorted_points = sorted(session['focus_points'], key=lambda x: x['timestamp'])
        
        for point in sorted_points:
            # Convert time to seconds from start
            time_delta = (point['timestamp'] - start_time).total_seconds()
            # Use 1 for focused, 0 for unfocused
            focus_value = 1 if point['is_focused'] else 0
            focus_series.append(time_delta, focus_value)
        
        # Add series to chart
        self.chart.addSeries(focus_series)
        
        # Set up new axes
        axis_x = QValueAxis()
        axis_x.setRange(0, session['duration'])
        axis_x.setTickCount(min(10, max(2, session['duration'] // 30)))  # Adaptive tick count
        axis_x.setTitleText("Time (seconds)")
        
        axis_y = QValueAxis()
        axis_y.setRange(-0.1, 1.1)  # Add a little padding above and below
        axis_y.setTickCount(3)  # Add one more tick for better visualization
        axis_y.setLabelFormat("%d")
        axis_y.setTitleText("Focus State")
        
        self.chart.addAxis(axis_x, Qt.AlignBottom)
        self.chart.addAxis(axis_y, Qt.AlignLeft)
        
        focus_series.attachAxis(axis_x)
        focus_series.attachAxis(axis_y)
        
        # Update chart title
        self.chart.setTitle(f"Focus Timeline - {session['start_time'].strftime('%Y-%m-%d %H:%M')}")
    
    def show_eye_analysis(self, session_id):
        """Show eye movement analysis for a session"""
        print(f"DEBUG: Showing eye analysis for session {session_id}")
        
        # Save original height before expanding
        if self.original_height is None:
            self.original_height = self.window().height()
            print(f"DEBUG: Saved original height: {self.original_height}")
        
        session = self.db_manager.get_session_details(session_id)
        if not session:
            print(f"ERROR: Failed to get session details for ID {session_id}")
            return
        
        self.current_session_id = session_id
        
        # Update session details header
        self.details_title.setText(f"Eye Movement Analysis - {session['start_time'].strftime('%Y-%m-%d %H:%M')}")
        
        # Check if eye movement data exists
        has_eye_data = False
        if 'eye_movement_data' in session and session['eye_movement_data']:
            has_eye_data = True
            self.eye_movement_status.setText(f"Eye Movement Data: Present - {len(session['eye_movement_data'].get('gaze_ratio_changes', []))} gaze changes, {len(session['eye_movement_data'].get('fixation_durations', []))} fixations")
            
            try:
                # Set the eye movement data for analysis
                print(f"DEBUG: Setting eye movement data on widget, type: {type(session['eye_movement_data'])}")
                self.eye_movement_widget.set_data(session['eye_movement_data'])
                print("DEBUG: Successfully set eye movement data on widget")
            except Exception as e:
                print(f"ERROR: Failed to set eye movement data: {e}")
                traceback.print_exc()
                self.eye_movement_status.setText(f"Error setting data: {str(e)}")
        else:
            print("DEBUG: No eye movement data in session")
            self.eye_movement_status.setText("Eye Movement Data: None available")
            
            # No eye movement data, show message
            try:
                self.eye_movement_widget.canvas.axes.clear()
                self.eye_movement_widget.canvas.axes.text(0.5, 0.5, "No eye movement data available for this session",
                                                  horizontalalignment='center',
                                                  verticalalignment='center',
                                                  transform=self.eye_movement_widget.canvas.axes.transAxes,
                                                  color='white',
                                                  fontsize=14)
                self.eye_movement_widget.canvas.draw()
            except Exception as e:
                print(f"ERROR: Failed to update canvas with message: {e}")
                traceback.print_exc()
        
        # Hide regular focus data, show eye movement analysis
        self.metrics_frame.setVisible(False)
        self.chart_frame.setVisible(False)
        self.eye_movement_container.setVisible(True)
        
        # Force size update for container and widget with increased height
        self.eye_movement_widget.setMinimumHeight(500)  # Increased from 400 to 500
        self.eye_movement_container.setMinimumHeight(600)  # Ensure container is also tall enough
        self.eye_movement_container.adjustSize()
        self.adjustSize()
        
        # Debug visibility state
        print(f"DEBUG: Visibility of containers: eye_movement={self.eye_movement_container.isVisible()}, "
              f"metrics={self.metrics_frame.isVisible()}, chart={self.chart_frame.isVisible()}")
        
        # Force update to ensure widget is displayed
        self.eye_movement_container.repaint()
        self.repaint()
    
    def show_focus_data(self):
        """Switch back to the focus data view"""
        print("DEBUG: Switching back to focus data view")
        
        # Hide eye movement analysis, show regular focus data
        self.eye_movement_container.setVisible(False)
        self.metrics_frame.setVisible(True)
        self.chart_frame.setVisible(True)
        
        # Restore original size if we expanded for eye movement analysis
        if self.original_height is not None:
            print(f"DEBUG: Restoring original height: {self.original_height}")
            main_window = self.window()
            current_size = main_window.size()
            main_window.resize(current_size.width(), self.original_height)
            self.original_height = None  # Reset for next time
        
        # Update title back to session details
        if self.current_session_id:
            session = self.db_manager.get_session_details(self.current_session_id)
            if session:
                self.details_title.setText(f"Session Details - {session['start_time'].strftime('%Y-%m-%d %H:%M')}")
        
        # Debug visibility state
        print(f"DEBUG: Visibility after switching: eye_movement={self.eye_movement_container.isVisible()}, "
              f"metrics={self.metrics_frame.isVisible()}, chart={self.chart_frame.isVisible()}")
        
        # Force update
        self.repaint()