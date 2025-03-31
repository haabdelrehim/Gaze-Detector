import cv2
from PyQt5.QtWidgets import (QMainWindow, QWidget,
                             QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QTabWidget)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt

from video_thread import VideoThread
from focus_metrics_widget import FocusMetricsWidget
from advice_widget import AdviceWidget

class FocusTrackerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.initUI()
        
        # Start video thread
        self.video_thread = VideoThread()
        self.video_thread.change_pixmap_signal.connect(self.update_image)
        self.video_thread.focus_data_signal.connect(self.update_focus_data)
        self.video_thread.start()
    
    def initUI(self):
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
        main_layout = QHBoxLayout(central_widget)
        
        # Left panel (video feed and controls)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
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
        """)
        
        self.reset_button = QPushButton("Reset")
        self.reset_button.setMinimumHeight(40)
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
        """)
        
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.pause_button)
        control_layout.addWidget(self.reset_button)
        
        left_layout.addLayout(control_layout)
        
        # Right panel (tabs for metrics and advice)
        right_panel = QTabWidget()
        right_panel.setMinimumWidth(400)
        
        # Metrics tab
        self.metrics_widget = FocusMetricsWidget()
        right_panel.addTab(self.metrics_widget, "Focus Metrics")
        
        # Advice tab
        self.advice_widget = AdviceWidget()
        
        right_panel.addTab(self.advice_widget, "Focus Advice")
        
        # Connect the generate advice button
        self.advice_widget.generate_button.clicked.connect(lambda: self.debug_and_generate())
        
        # Add panels to main layout
        main_layout.addWidget(left_panel, 2)
        main_layout.addWidget(right_panel, 1)
        
        self.setCentralWidget(central_widget)
        
        # Connect button signals
        self.start_button.clicked.connect(self.start_session)
        self.pause_button.clicked.connect(self.pause_session)
        self.reset_button.clicked.connect(self.reset_session)
        
        # Focus data
        self.focus_data = {}
    
    def debug_and_generate(self):
        print("Generate button clicked!")
        if hasattr(self.advice_widget, 'model_loading') and self.advice_widget.model_loading:
            print("Model is still loading. Cannot generate advice yet.")
            return
        self.advice_widget.generate_gemini_advice()
    
    
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
        print("Main app received focus data update")
        self.focus_data = focus_data
        self.metrics_widget.update_metrics(focus_data)
        
        # Only update advice occasionally to avoid overwhelming the user
        if focus_data["distraction_count"] % 5 == 0 and focus_data["distraction_count"] > 0:
            self.advice_widget.update_advice(focus_data)
    
    def start_session(self):
        """Start or resume the focus tracking session"""
        self.video_thread.start_tracking()
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.reset_button.setEnabled(True)
    
    def pause_session(self):
        """Pause the focus tracking session"""
        self.video_thread.pause_tracking()
        self.start_button.setEnabled(True)
        self.start_button.setText("Resume Session")
        self.pause_button.setEnabled(False)
    
    def reset_session(self):
        """Reset all session data"""
        self.video_thread.reset()
        self.start_button.setEnabled(True)
        self.start_button.setText("Start Session")
        self.pause_button.setEnabled(False)
    
    def generate_advice(self):
        """Generate focus advice based on current metrics"""
        if self.focus_data:
            self.advice_widget.update_advice(self.focus_data)
    
    def closeEvent(self, event):
        """Clean up resources when closing the application"""
        self.video_thread.stop()
        if hasattr(self.advice_widget, 'api_thread'):
            self.advice_widget.api_thread.stop()
        event.accept()