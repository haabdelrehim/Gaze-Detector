import os
import traceback
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
import google.generativeai as genai

class APIThread(QThread):
    advice_ready_signal = pyqtSignal(str)
    
    def __init__(self, api_key=None):
        super().__init__()
        # Don't hardcode the API key - use the provided one or look for environment variable
        api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("Warning: No Gemini API key provided. Using default key.")
            api_key = "AIzaSyCqQ3LNxb6LMpJgkvfxMMNkUrIcIcA8I5w" # Better to use environment variable
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")
        self.focus_data = None
        self.running = True
        
        # Signal we're ready after initialization
        QTimer.singleShot(1000, lambda: self.advice_ready_signal.emit("<p>Gemini API initialized successfully!</p>"))
    
    def set_focus_data(self, focus_data):
        print("APIThread received focus data:", focus_data)
        self.focus_data = focus_data
    
    def run(self):
        try:
            print("API thread started")
            
            while self.running:
                if self.focus_data is not None:
                    print("APIThread processing focus data")
                    try:
                        advice = self.generate_advice(self.focus_data)
                        print("Advice generated successfully")
                        self.advice_ready_signal.emit(advice)
                    except Exception as e:
                        print(f"Error generating advice: {e}")
                        traceback.print_exc()
                        self.advice_ready_signal.emit(f"<p>Error generating advice: {str(e)}</p>")
                    finally:
                        # Always clear the focus data even if an error occurred
                        print("Clearing focus data")
                        self.focus_data = None
                
                self.msleep(100)
            
        except Exception as e:
            print(f"Fatal error in API thread: {e}")
            traceback.print_exc()
            self.advice_ready_signal.emit(f"<p>Error in API thread: {str(e)}</p>")
    
    def generate_advice(self, focus_data):
        print("Starting advice generation with Gemini API")
        try:
            # Extract metrics
            focus_duration = focus_data["focus_duration"]
            distraction_count = focus_data["distraction_count"]
            avg_distraction_time = focus_data["avg_distraction_time"]
            
            # Add more context for better advice
            minutes_focused = focus_duration / 60
            current_status = "focused" if focus_data["focused"] else "distracted"
            gaze_direction = focus_data["direction"]
            
            # Format the prompt for Gemini
            prompt = (
                f"You are a focus assistant. Provide 2-3 tips for improving focus. "
                f"User has been focused for {minutes_focused:.1f} minutes with {distraction_count} distractions. "
                f"Average distraction time is {avg_distraction_time:.1f} seconds. "
                f"User is currently {current_status} and looking {gaze_direction}. "
                f"Keep your advice brief, clear, and practical."
            )
            
            # Send the request to the Gemini API
            response = self.model.generate_content(prompt)
            
            if not response:
                return "<p>No response received from Gemini API</p>"
            
            generated_text = response.text.strip()
            
            # Format the response with HTML
            generated_html = f"<h3>Focus Recommendations</h3><p>{generated_text}</p>"
            
            print("Generated advice successfully")
            return generated_html
            
        except Exception as e:
            print(f"Exception in generate_advice: {str(e)}")
            traceback.print_exc()
            return f"<p>Error generating advice: {str(e)}</p>"
    
    def stop(self):
        self.running = False
        self.wait()