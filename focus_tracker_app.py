import cv2
from PyQt5.QtWidgets import (QMainWindow, QWidget,
                             QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QTabWidget,
                             QMessageBox)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, QDateTime, QTimer
from datetime import datetime

from video_thread import VideoThread
from focus_metrics_widget import FocusMetricsWidget
from advice_widget import AdviceWidget
from database_manager import DatabaseManager
from history_widget import HistoryWidget


class FocusTrackerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Initialize database
        self.db_manager = DatabaseManager()
        
        # Initialize session tracking variables
        self.session_active = False
        self.session_start_time = None
        self.session_focus_points = []  # To store focus data points for the current session
        self.focus_data_snapshots = []  # To store periodic snapshots of focus data
        self.current_focus_period_start = None  # For tracking continuous focus periods
        self.longest_focus_period = 0  # Track longest continuous focus period in seconds
        
        # Initialize UI
        self.initUI()
        
        # Start video thread
        self.video_thread = VideoThread()
        self.video_thread.change_pixmap_signal.connect(self.update_image)
        self.video_thread.focus_data_signal.connect(self.update_focus_data)
        self.video_thread.start()
        
        # Session data collection timer - records focus state at regular intervals
        self.data_collection_timer = QTimer()
        self.data_collection_timer.timeout.connect(self.collect_session_data)
        self.data_collection_timer.setInterval(5000)  # Every 5 seconds
    
    def initUI(self):
        """Initialize the user interface"""
        self.setWindowTitle("FocusTrack - Eye Tracking Focus Assistant")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet("""
        QMainWindow, QWidget {
            background-color: #2D2D30;
            color: #E0E0E0;
        }
        QLabel {
            color: #E0E0E0;
        }
        QTabWidget::pane {
            border: 1px solid #3E3E42;
            background-color: #2D2D30;
        }
        QTabBar::tab {
            background-color: #3E3E42;
            color: #E0E0E0;
            padding: 8px 12px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        QTabBar::tab:selected {
            background-color: #007ACC;
        }
        QTabBar::tab:hover:!selected {
            background-color: #505050;
        }
        """)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.main_layout = QHBoxLayout(central_widget)
        
        # Create all widgets first before assembling layout
        # Create the metrics widget
        self.metrics_widget = FocusMetricsWidget()
        
        # Create the advice widget
        self.advice_widget = AdviceWidget()
        
        # Create the history widget
        self.history_widget = HistoryWidget(self.db_manager)
        
        # Left panel (video feed and controls)
        self.left_panel = QWidget()
        left_layout = QVBoxLayout(self.left_panel)
        
        # Video display
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet("border: 1px solid #555555; background-color: black;")
        left_layout.addWidget(self.video_label)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start Session")
        self.start_button.setMinimumHeight(40)
        self.start_button.setStyleSheet("""
        QPushButton {
            background-color: #4CAF50;
            color: white;
            border-radius: 5px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        """)
        
        self.pause_button = QPushButton("Pause")
        self.pause_button.setMinimumHeight(40)
        self.pause_button.setEnabled(False)
        self.pause_button.setStyleSheet("""
        QPushButton {
            background-color: #f39c12;
            color: white;
            border-radius: 5px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #e67e22;
        }
        QPushButton:disabled {
            background-color: #7f7f7f;
            color: #cccccc;
        }
        """)
        
        self.reset_button = QPushButton("End Session")
        self.reset_button.setMinimumHeight(40)
        self.reset_button.setEnabled(False)
        self.reset_button.setStyleSheet("""
        QPushButton {
            background-color: #e74c3c;
            color: white;
            border-radius: 5px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #c0392b;
        }
        QPushButton:disabled {
            background-color: #7f7f7f;
            color: #cccccc;
        }
        """)
        
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.pause_button)
        control_layout.addWidget(self.reset_button)
        
        left_layout.addLayout(control_layout)
        
        # Right panel (tabs for metrics, advice, and history)
        self.right_panel = QTabWidget()
        self.right_panel.setMinimumWidth(400)
        
        # Add tabs
        self.right_panel.addTab(self.metrics_widget, "Focus Metrics")
        self.right_panel.addTab(self.advice_widget, "Focus Advice")
        self.right_panel.addTab(self.history_widget, "Session History")
        
        # Connect tab change signal
        self.right_panel.currentChanged.connect(self.on_tab_changed)
        
        # Connect advice button
        self.advice_widget.generate_button.clicked.connect(self.generate_advice)
        
        # Add panels to main layout
        self.main_layout.addWidget(self.left_panel, 2)
        self.main_layout.addWidget(self.right_panel, 1)
        
        self.setCentralWidget(central_widget)
        
        # Connect tab change signal
        self.right_panel.currentChanged.connect(self.on_tab_changed)

        # Connect advice button
        self.advice_widget.generate_button.clicked.connect(self.generate_advice)

        # Add panels to main layout
        self.main_layout.addWidget(self.left_panel, 2)
        self.main_layout.addWidget(self.right_panel, 1)
        self.setCentralWidget(central_widget)

        # First ensure there are no existing connections
        print("Checking existing button connections")
        try:
            self.start_button.clicked.disconnect()
            print("Disconnected existing start button connections")
        except TypeError:
            print("No existing start button connections to disconnect")

        try:
            self.pause_button.clicked.disconnect()
            print("Disconnected existing pause button connections")
        except TypeError:
            print("No existing pause button connections to disconnect")

        try:
            self.reset_button.clicked.disconnect()
            print("Disconnected existing reset button connections")
        except TypeError:
            print("No existing reset button connections to disconnect")

        # Now connect all buttons
        print("Connecting buttons to their handlers")
        self.start_button.clicked.connect(self.start_session)
        self.pause_button.clicked.connect(self.pause_session)
        self.reset_button.clicked.connect(self.end_session)

        # Verify connections
        print(f"Start button has {self.start_button.receivers(self.start_button.clicked)} connections")
        print(f"Pause button has {self.pause_button.receivers(self.pause_button.clicked)} connections")
        print(f"Reset button has {self.reset_button.receivers(self.reset_button.clicked)} connections")

        # Debug output to check for multiple connections
        print(f"Button connections established:")
        print(f"  - Start button has {self.start_button.receivers(self.start_button.clicked)} connections")
        print(f"  - Pause button has {self.pause_button.receivers(self.pause_button.clicked)} connections")
        print(f"  - End button has {self.reset_button.receivers(self.reset_button.clicked)} connections")
        
        # Focus data
        self.focus_data = {}
    
    
    def update_image(self, cv_img):
        """Updates the image_label with a new OpenCV image"""
        qt_img = self.convert_cv_qt(cv_img)
        self.video_label.setPixmap(qt_img)
    
    def convert_cv_qt(self, cv_img):
        """Convert from OpenCV image to QPixmap"""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(self.video_label.width(), self.video_label.height(), Qt.KeepAspectRatio)
        return QPixmap.fromImage(p)
    
    def update_focus_data(self, focus_data):
        """Update the focus data and metrics"""
        self.focus_data = focus_data
        self.metrics_widget.update_metrics(focus_data)
        
        # Only update advice occasionally to avoid overwhelming the user
        if focus_data["distraction_count"] % 5 == 0 and focus_data["distraction_count"] > 0:
            self.advice_widget.update_advice(focus_data)
        
        # Track focus periods for session history
        if self.session_active:
            # If current state is focused and we're just starting a focus period
            if focus_data["focused"] and self.current_focus_period_start is None:
                self.current_focus_period_start = QDateTime.currentDateTime()
            
            # If current state is unfocused and we were in a focus period
            elif not focus_data["focused"] and self.current_focus_period_start is not None:
                # Calculate focus period duration
                focus_period = self.current_focus_period_start.secsTo(QDateTime.currentDateTime())
                
                # Check if this is the longest focus period
                if focus_period > self.longest_focus_period:
                    self.longest_focus_period = focus_period
                
                # Reset current focus period
                self.current_focus_period_start = None
    
    def collect_session_data(self):
        """Collect data points for the current session"""
        if not self.session_active:
            return
        
        # Create a timestamp for this data point
        current_time = datetime.now()
        
        # Store focus state with timestamp
        self.session_focus_points.append({
            'timestamp': current_time,
            'is_focused': self.focus_data["focused"],
            'gaze_direction': self.focus_data["direction"]
        })
        
        # Store a snapshot of all focus metrics periodically
        self.focus_data_snapshots.append({
            'timestamp': current_time,
            'focus_duration': self.focus_data["focus_duration"],
            'distraction_count': self.focus_data["distraction_count"],
            'avg_distraction_time': self.focus_data["avg_distraction_time"],
            'is_focused': self.focus_data["focused"],
            'direction': self.focus_data["direction"]
        })
    def on_tab_changed(self, index):
        """Handle tab changes to optimize layout"""
        tab_name = self.right_panel.tabText(index)
        
        if tab_name == "Session History":
            # Store original size before modifying
            self.original_window_width = self.width()
            self.original_window_height = self.height()
            
            # Hide the left panel (video feed) and expand history
            self.left_panel.setVisible(False)
            
            # Don't set minimum width here - that's causing the expansion
            # Instead, let it take up the space naturally when left panel is hidden
        else:
            # Show the left panel
            self.left_panel.setVisible(True)
            
            # If coming from history tab, restore original size
            if hasattr(self, 'original_window_width'):
                self.resize(self.original_window_width, self.original_window_height)
        
        # Force layout update
        self.adjustSize()
    def start_session(self):
        """Start or resume the focus tracking session"""
        if not self.session_active:
            # Starting a new session
            self.session_active = True
            self.session_start_time = QDateTime.currentDateTime()
            self.session_focus_points = []
            self.focus_data_snapshots = []
            self.longest_focus_period = 0
            self.current_focus_period_start = None
            
            # Start focus tracking
            self.video_thread.start_tracking()
            
            # Start data collection timer
            self.data_collection_timer.start()
            
            # Update UI
            self.start_button.setText("Resume")
            self.start_button.setEnabled(False)
            self.pause_button.setEnabled(True)
            self.reset_button.setEnabled(True)
        else:
            # Resuming a paused session
            self.video_thread.resume()
            self.data_collection_timer.start()
            
            # If we were focused when paused, restart the focus period timer
            if self.focus_data["focused"]:
                self.current_focus_period_start = QDateTime.currentDateTime()
            
            # Update UI
            self.start_button.setEnabled(False)
            self.pause_button.setEnabled(True)
    
    def pause_session(self):
        """Pause the focus tracking session"""
        if self.session_active:
            # Pause focus tracking
            self.video_thread.pause_tracking()
            
            # Pause data collection timer
            self.data_collection_timer.stop()
            
            # If we're in a focus period, end it since we're pausing
            if self.current_focus_period_start is not None:
                focus_period = self.current_focus_period_start.secsTo(QDateTime.currentDateTime())
                if focus_period > self.longest_focus_period:
                    self.longest_focus_period = focus_period
                self.current_focus_period_start = None
            
            # Update UI
            self.start_button.setEnabled(True)
            self.pause_button.setEnabled(False)

    
    def end_session(self):
        """End the current session and save to database"""
        # Print call stack to see what's calling this method
        import traceback
        print("\n========== END SESSION CALL STACK ==========")
        traceback.print_stack()
        print("============================================\n")
        
        if not self.session_active:
            print("Session not active, returning early")
            return
            
        # Add a flag to prevent duplicate session saving
        if hasattr(self, '_saving_in_progress') and self._saving_in_progress:
            print("Session save already in progress, ignoring duplicate call")
            return
            
        print("Starting session saving process")
        self._saving_in_progress = True

        try:
            # Stop tracking and data collection
            self.video_thread.pause_tracking()
            self.data_collection_timer.stop()
            
            # Calculate session metrics
            end_time = QDateTime.currentDateTime()
            session_duration = self.session_start_time.secsTo(end_time)
            
            # If we're still in a focus period, include it in longest period calculation
            if self.current_focus_period_start is not None:
                focus_period = self.current_focus_period_start.secsTo(end_time)
                if focus_period > self.longest_focus_period:
                    self.longest_focus_period = focus_period
            
            # Calculate focus percentage (time focused / total time)
            focus_time = self.focus_data["focus_duration"]
            focus_percentage = (focus_time / session_duration * 100) if session_duration > 0 else 0
            
            print(f"\n========== SESSION DATA SUMMARY ==========")
            print(f"Session duration: {session_duration} seconds")
            print(f"Number of focus points: {len(self.session_focus_points)}")
            print(f"Number of focus snapshots: {len(self.focus_data_snapshots)}")
            print(f"Distraction count: {self.focus_data['distraction_count']}")

            # If the session data is very large, limit it to prevent database issues
            MAX_FOCUS_POINTS = 500
            if len(self.session_focus_points) > MAX_FOCUS_POINTS:
                print(f"Limiting focus points from {len(self.session_focus_points)} to {MAX_FOCUS_POINTS}")
                # Keep first, middle, and last points for a representative sample
                first_third = self.session_focus_points[:MAX_FOCUS_POINTS//3]
                middle_third = self.session_focus_points[len(self.session_focus_points)//2 - MAX_FOCUS_POINTS//6:
                                                        len(self.session_focus_points)//2 + MAX_FOCUS_POINTS//6]
                last_third = self.session_focus_points[-MAX_FOCUS_POINTS//3:]
                self.session_focus_points = first_third + middle_third + last_third

            MAX_SNAPSHOTS = 100
            if len(self.focus_data_snapshots) > MAX_SNAPSHOTS:
                print(f"Limiting focus snapshots from {len(self.focus_data_snapshots)} to {MAX_SNAPSHOTS}")
                # Same approach - keep beginning, middle, and end
                first_third = self.focus_data_snapshots[:MAX_SNAPSHOTS//3]
                middle_third = self.focus_data_snapshots[len(self.focus_data_snapshots)//2 - MAX_SNAPSHOTS//6:
                                                        len(self.focus_data_snapshots)//2 + MAX_SNAPSHOTS//6]
                last_third = self.focus_data_snapshots[-MAX_SNAPSHOTS//3:]
                self.focus_data_snapshots = first_third + middle_third + last_third
            
            # Prepare session data for database
            session_data = {
                'start_time': self.session_start_time.toPyDateTime(),
                'end_time': end_time.toPyDateTime(),
                'duration': session_duration,
                'distraction_count': self.focus_data["distraction_count"],
                'avg_distraction_time': self.focus_data["avg_distraction_time"],
                'focus_percentage': focus_percentage,
                'longest_focus_period': self.longest_focus_period,
                'focus_data': self.focus_data_snapshots,
                'focus_points': self.session_focus_points
            }
            
            # Save session to database
            print("Attempting to save session to database...")
            session_id = self.db_manager.save_session(session_data)
            
            if session_id:
                print(f"Successfully saved session with ID: {session_id}")
                QMessageBox.information(
                    self, 
                    "Session Completed", 
                    f"Session completed and saved to history.\n\nDuration: {session_duration // 60} minutes, {session_duration % 60} seconds\nFocus percentage: {focus_percentage:.1f}%"
                )
                
                # Reset session state
                self.session_active = False
                self.video_thread.reset()
                
                # Reset UI
                self.start_button.setText("Start Session")
                self.start_button.setEnabled(True)
                self.pause_button.setEnabled(False)
                self.reset_button.setEnabled(False)
                
                # Refresh history tab
                self.history_widget.refresh_sessions()
            else:
                print("Failed to save session - session_id is None")
                QMessageBox.warning(
                    self, 
                    "Error Saving Session", 
                    "There was an error saving the session to history. Check console for details."
                )
        except Exception as e:
            import traceback
            print(f"Exception during session saving: {e}")
            traceback.print_exc()
            QMessageBox.critical(
                self, 
                "Error Saving Session", 
                f"An exception occurred: {str(e)}\nSee console for details."
            )
            print("<<< EXITING: end_session (normal completion)")
        except Exception as e:
            print("<<< EXITING: end_session (with exception)")
            raise
        finally:
            # Reset the flag when done, regardless of success or failure
            print("Session saving process completed, resetting flag")
            self._saving_in_progress = False
    
    def generate_advice(self):
        """Generate focus advice based on current metrics"""
        if self.focus_data:
            self.advice_widget.generate_gemini_advice()

    def closeEvent(self, event):
        """Handle application close event"""
        print(">>> ENTERING: closeEvent")
        
        # If a session is active, ask to save it
        if self.session_active:
            print("Session active during closeEvent")
            reply = QMessageBox.question(
                self, 
                "End Session", 
                "A session is still in progress. Would you like to save it before exiting?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Yes:
                print("User chose to save session before exit")
                self.end_session()
            elif reply == QMessageBox.Cancel:
                print("User cancelled application close")
                event.ignore()
                print("<<< EXITING: closeEvent (cancelled)")
                return
        
        # Clean up resources
        print("Cleaning up resources")
        self.video_thread.stop()
        if hasattr(self.advice_widget, 'api_thread'):
            self.advice_widget.api_thread.stop()
        
        # Close database connection
        self.db_manager.close()
        
        print("<<< EXITING: closeEvent (completed)")
        event.accept()