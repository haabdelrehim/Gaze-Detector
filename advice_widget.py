import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QTextEdit)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import QTimer

from api_thread import APIThread

class AdviceWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        
        # Initialize API thread
        api_key = os.environ.get("GEMINI_API_KEY", "") # Get from environment variable
        self.api_thread = APIThread(api_key)
        self.api_thread.advice_ready_signal.connect(self.set_advice_text)
        self.api_thread.advice_ready_signal.connect(lambda msg: self.update_model_status(True, "Ready"))
        self.api_thread.start()
        
        # Track if advice is being generated
        self.generating_advice = False
        self.model_loading = True # Start with loading state
    
    def initUI(self):
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Focus Advice")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)
        
        # Model status indicator
        self.model_status_layout = QHBoxLayout()
        self.model_status_label = QLabel("Model Status:")
        self.model_status_indicator = QLabel()
        self.model_status_indicator.setFixedSize(20, 20)
        self.model_status_indicator.setStyleSheet("background-color: yellow; border-radius: 10px;")
        self.model_status_text = QLabel("Loading...")
        
        self.model_status_layout.addWidget(self.model_status_label)
        self.model_status_layout.addWidget(self.model_status_indicator)
        self.model_status_layout.addWidget(self.model_status_text)
        self.model_status_layout.addStretch()
        
        layout.addLayout(self.model_status_layout)
        
        # Advice text area
        self.advice_text = QTextEdit()
        self.advice_text.setReadOnly(True)
        self.advice_text.setMinimumHeight(150)
        self.advice_text.setStyleSheet("background-color: #333337; border: 1px solid #555555; border-radius: 5px; color: #E0E0E0;")
        
        # Set initial advice
        self.advice_text.setHtml("""
        <h3>Welcome to FocusTrack!</h3>
        <p>This application will help you monitor and improve your focus while working on your computer.</p>
        <p>Some tips to get started:</p>
        <ul>
        <li>Make sure you are in a well-lit environment</li>
        <li>Position yourself approximately 50-70cm from the camera</li>
        <li>Try to keep your head relatively stable while working</li>
        </ul>
        <p>As you use the application, we'll provide personalized advice based on your focus patterns.</p>
        <p>Please wait while the Gemini model is loading...</p>
        """)
        
        layout.addWidget(self.advice_text)
        
        # Generate advice button
        self.generate_button = QPushButton("Generate Advice")
        self.generate_button.setMinimumHeight(40)
        self.generate_button.setStyleSheet("""
        QPushButton {
            background-color: #4CAF50;
            color: white;
            border-radius: 5px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QPushButton:disabled {
            background-color: #cccccc;
            color: #666666;
        }
        """)
        self.generate_button.setEnabled(False) # Disabled until model is loaded
        layout.addWidget(self.generate_button)
        
        self.setLayout(layout)
    
    def update_model_status(self, loaded, message):
        """Update the model status indicator"""
        if loaded:
            self.model_status_indicator.setStyleSheet("background-color: green; border-radius: 10px;")
            self.model_status_text.setText("Ready")
            self.generate_button.setEnabled(True)
            self.model_loading = False
        else:
            self.model_status_indicator.setStyleSheet("background-color: yellow; border-radius: 10px;")
            self.model_status_text.setText(message)
            self.generate_button.setEnabled(False)
            self.model_loading = True
    
    def generate_gemini_advice(self):
        print("generate_gemini_advice called")
        if hasattr(self, 'current_focus_data'):
            print("Focus data available:", self.current_focus_data)
            self.generating_advice = True
            self.generate_button.setEnabled(False)
            self.advice_text.setHtml("<p>Generating personalized advice using Gemini API...</p>")
            
            # Send focus data to API thread
            self.api_thread.set_focus_data(self.current_focus_data)
            QTimer.singleShot(15000, self.check_advice_generation)
        else:
            self.advice_text.setHtml("<p>No focus data available. Please start a focus tracking session first.</p>")
    
    
    def check_advice_generation(self):
        if self.generating_advice:
            self.advice_text.setHtml("""
            <h3>Focus Recommendations</h3>
            <p>Sorry, I couldn't generate personalized advice at this time. Here are some general focus tips:</p>
            <ul>
            <li>Take regular short breaks (5 minutes) every 25-30 minutes of focused work</li>
            <li>Remove distractions from your workspace</li>
            <li>Use the Pomodoro Technique to structure your work sessions</li>
            <li>Stay hydrated and maintain good posture</li>
            </ul>
            <p>You can try generating advice again later.</p>
            """)
            self.generating_advice = False
            self.generate_button.setEnabled(True)
            self.generate_button.setText("Generate Advice")
    
    def set_advice_text(self, advice_html):
        print("Setting advice text:", advice_html[:100] + "..." if len(advice_html) > 100 else advice_html)
        self.advice_text.setHtml(advice_html)
        self.generating_advice = False
        self.generate_button.setEnabled(True)
        self.generate_button.setText("Generate Advice")
    
    def update_advice(self, focus_data):
        print("update_advice called with:", focus_data)
        # Store the focus data for when the user clicks generate
        self.current_focus_data = focus_data
        
        # Simple rule-based advice for immediate feedback
        distraction_count = focus_data["distraction_count"]
        is_focused = focus_data["focused"]
        
        # Just update a status indicator immediately
        status_html = "<h3>Focus Status</h3>"
        if is_focused:
            status_html += f"<p>Currently: <span style='color: green; font-weight: bold;'>Focused</span></p>"
        else:
            status_html += f"<p>Currently: <span style='color: red; font-weight: bold;'>Distracted</span></p>"
        
        status_html += f"<p>Distraction count: {distraction_count}</p>"
        
        if self.model_loading:
            status_html += "<p>Model is still loading. Please wait before generating advice.</p>"
        else:
            status_html += "<p>Click 'Generate AI Advice' for personalized recommendations</p>"
        
        # Only update the status part, not the whole advice
        if not self.generating_advice:
            self.advice_text.setHtml(status_html)