import sys
import cv2
import numpy as np
import dlib
from math import hypot
from PyQt5.QtCore import Qt, QDateTime, pyqtSignal, QThread

class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)
    focus_data_signal = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.paused = False
        self.tracking = False
        # Eye movement dynamics tracking
        self.gaze_ratio_changes = []     # Store changes in gaze ratio (for saccades)
        self.fixation_durations = []     # Store durations of fixations
        self.last_gaze_ratio = None      # Previous gaze ratio for comparison
        self.fixation_start_time = None  # When current fixation started
        self.in_fixation = False         # Currently in fixation state
        self.gaze_change_threshold = 0.8 # Threshold to detect a saccade
        self.min_fixation_duration = 0.3  # Minimum time in seconds to count as fixation
        self.saccade_confirmation_count = 0  # Counter for consecutive frames with significant change
        self.saccade_confirmation_threshold = 2  # Number of frames needed to confirm a saccade
        
        # Initialize eye tracking components
        self.detector = dlib.get_frontal_face_detector()
        try:
            self.predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")
        except RuntimeError:
            print("Error: Could not load the face landmarks model file.")
            sys.exit(1)
        
        # Focus tracking variables
        self.is_focused = True
        self.focus_start_time = QDateTime.currentDateTime()
        self.distraction_start_time = None
        self.distraction_periods = []
        self.gaze_ratio_history = []
        self.focus_data = {
            "focused": True,
            "direction": "CENTER",
            "blinking": False,
            "focus_duration": 0,
            "distraction_count": 0,
            "avg_distraction_time": 0
        }

    def start_tracking(self):
        self.tracking = True
        if not self.is_focused:
            self.is_focused = True
            self.focus_start_time = QDateTime.currentDateTime()
            self.distraction_start_time = None
        self.focus_data_signal.emit(self.focus_data)
    
    def pause_tracking(self):
        self.tracking = False
    
    
    def midpoint(self, p1, p2):
        return int((p1.x + p2.x)/2), int((p1.y + p2.y)/2)
    
    def get_blinking_ratio(self, eye_points, facial_landmarks):
        left_point = (facial_landmarks.part(eye_points[0]).x, facial_landmarks.part(eye_points[0]).y)
        right_point = (facial_landmarks.part(eye_points[3]).x, facial_landmarks.part(eye_points[3]).y)
        center_top = self.midpoint(facial_landmarks.part(eye_points[1]), facial_landmarks.part(eye_points[2]))
        center_bottom = self.midpoint(facial_landmarks.part(eye_points[5]), facial_landmarks.part(eye_points[4]))
        
        ver_line_length = hypot((center_top[0] - center_bottom[0]), (center_top[1] - center_bottom[1]))
        hor_line_length = hypot((left_point[0] - right_point[0]), (left_point[1] - right_point[1]))
        
        ratio = hor_line_length/ver_line_length if ver_line_length > 0 else 1
        return ratio
    
    def get_gaze_ratio(self, eye_points, facial_landmarks, frame, gray):
        left_eye_region = np.array([(facial_landmarks.part(eye_points[0]).x, facial_landmarks.part(eye_points[0]).y),
                                    (facial_landmarks.part(eye_points[1]).x, facial_landmarks.part(eye_points[1]).y),
                                    (facial_landmarks.part(eye_points[2]).x, facial_landmarks.part(eye_points[2]).y),
                                    (facial_landmarks.part(eye_points[3]).x, facial_landmarks.part(eye_points[3]).y),
                                    (facial_landmarks.part(eye_points[4]).x, facial_landmarks.part(eye_points[4]).y),
                                    (facial_landmarks.part(eye_points[5]).x, facial_landmarks.part(eye_points[5]).y)], np.int32)
        
        height, width, _ = frame.shape
        mask = np.zeros((height, width), np.uint8)
        cv2.polylines(mask, [left_eye_region], True, 255, 2)
        cv2.fillPoly(mask, [left_eye_region], 255)
        eye = cv2.bitwise_and(gray, gray, mask=mask)
        
        min_x = np.min(left_eye_region[:,0])
        max_x = np.max(left_eye_region[:,0])
        min_y = np.min(left_eye_region[:,1])
        max_y = np.max(left_eye_region[:,1])
        
        if min_x < max_x and min_y < max_y and min_x >= 0 and min_y >= 0 and max_x < width and max_y < height:
            gray_eye = eye[min_y:max_y, min_x:max_x]
            if gray_eye.size > 0:
                _, threshold_eye = cv2.threshold(gray_eye, 70, 255, cv2.THRESH_BINARY)
                height, width = threshold_eye.shape
                
                if width > 1: # Make sure we can divide the eye
                    left_side_threshold = threshold_eye[0:height, 0:int(width/2)]
                    left_side_white = cv2.countNonZero(left_side_threshold)
                    
                    right_side_threshold = threshold_eye[0:height, int(width/2):width]
                    right_side_white = cv2.countNonZero(right_side_threshold)
                    
                    if left_side_white == 0:
                        gaze_ratio = 1
                    elif right_side_white == 0:
                        gaze_ratio = 5
                    else:
                        gaze_ratio = left_side_white/right_side_white
                    
                    return gaze_ratio
                
        return 1 # Default to center if we can't calculate
    
    def update_focus_data(self, is_looking_at_screen, is_blinking, gaze_direction):
        if not self.tracking:
            return
        if self.paused:
            return
        
        current_time = QDateTime.currentDateTime()
        
        # Update focus/distraction tracking
        if is_looking_at_screen and not self.is_focused:
            # Transition: Distracted -> Focused
            if self.distraction_start_time:
                distraction_duration = self.distraction_start_time.secsTo(current_time)
                self.distraction_periods.append(distraction_duration)
                self.distraction_start_time = None
            self.is_focused = True
            self.focus_start_time = current_time
        elif not is_looking_at_screen and self.is_focused:
            # Transition: Focused -> Distracted
            self.is_focused = False
            self.distraction_start_time = current_time
            self.focus_data["distraction_count"] += 1
        
        # Calculate focus metrics
        focus_duration = self.focus_start_time.secsTo(current_time) if self.is_focused else 0
        
        # Calculate average distraction time
        avg_distraction = 0
        if self.distraction_periods:
            avg_distraction = sum(self.distraction_periods) / len(self.distraction_periods)
        
        # Update focus data dictionary
        self.focus_data.update({
            "focused": is_looking_at_screen,
            "direction": gaze_direction,
            "blinking": is_blinking,
            "focus_duration": focus_duration,
            "avg_distraction_time": avg_distraction
        })
        
        # Emit the focus data signal
        self.focus_data_signal.emit(self.focus_data)
    
    def run(self):
        cap = cv2.VideoCapture(1)
        if cap.isOpened():
            print("Camera 1 opened successfully")
        else:
            print("Error: Camera 1 not accessible!")
            return
        
        if not cap.isOpened():
            print("Error: No cameras accessible!")
            return
        
        while self.running:
            if self.paused:
                # If paused, still emit the last frame but don't process
                cv2.waitKey(100) # Small delay to reduce CPU usage
                continue
            
            ret, frame = cap.read()
            if not ret:
                print("Error: Failed to capture frame")
                break
            
            # Flip the frame horizontally for a more intuitive mirror view
            frame = cv2.flip(frame, 1)
            
            # Process frame for eye tracking
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.detector(gray)
            
            is_blinking = False
            gaze_direction = "CENTER" # Default
            is_looking_at_screen = True # Default
            
            for face in faces:
                landmarks = self.predictor(gray, face)
                
                # Detect blinking
                left_eye_ratio = self.get_blinking_ratio([36,37,38,39,40,41], landmarks)
                right_eye_ratio = self.get_blinking_ratio([42,43,44,45,46,47], landmarks)
                blinking_ratio = (left_eye_ratio + right_eye_ratio)/2
                
                if blinking_ratio > 5.2:
                    is_blinking = True
                    cv2.putText(frame, "BLINKING", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
                else:
                    # Gaze detection only if not blinking
                    gaze_ratio_left_eye = self.get_gaze_ratio([36,37,38,39,40,41], landmarks, frame, gray)
                    gaze_ratio_right_eye = self.get_gaze_ratio([42,43,44,45,46,47], landmarks, frame, gray)
                    gaze_ratio = (gaze_ratio_left_eye + gaze_ratio_right_eye)/2
                    
                    self.gaze_ratio_history.append(gaze_ratio)
                    if len(self.gaze_ratio_history) > 10: # Increase history for smoother results
                        self.gaze_ratio_history.pop(0)
                    
                    avg_gaze_ratio = sum(self.gaze_ratio_history)/len(self.gaze_ratio_history)
                    
                    
                    # Determine gaze direction and focus state
                    if avg_gaze_ratio < 0.45:
                        gaze_direction = "RIGHT"
                        is_looking_at_screen = False
                        cv2.putText(frame, "RIGHT", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    elif 0.45 <= avg_gaze_ratio <= 5.5:
                        gaze_direction = "CENTER"
                        cv2.putText(frame, "CENTER", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    else:
                        gaze_direction = "LEFT"
                        is_looking_at_screen = False
                        cv2.putText(frame, "LEFT", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                self.track_gaze_changes(avg_gaze_ratio)
                if not is_blinking:
                    # Show detected eye movements on the frame
                    # Display counts in top-right corner
                    saccade_text = f"Saccades: {len(self.gaze_ratio_changes)}"
                    fixation_text = f"Fixations: {len(self.fixation_durations)}"
                    cv2.putText(frame, saccade_text, (frame.shape[1] - 200, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                    cv2.putText(frame, fixation_text, (frame.shape[1] - 200, 90),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                    
                    # Display a visual indicator when a saccade is detected
                    if self.saccade_confirmation_count > 0:
                        indicator_size = min(30, self.saccade_confirmation_count * 10)
                        cv2.circle(frame, (frame.shape[1] - 50, 120), 
                                indicator_size, (0, 165, 255), -1)
                
                # Update focus tracking data
                self.update_focus_data(is_looking_at_screen, is_blinking, gaze_direction)
                
                # Draw focus indicator
                indicator_color = (0, 255, 0) if is_looking_at_screen else (0, 0, 255)
                cv2.rectangle(frame, (10, 10), (30, 30), indicator_color, -1)
                
                # Draw facial landmarks if a face is detected
                for n in range(36, 48): # Loop through eye landmarks
                    x = landmarks.part(n).x
                    y = landmarks.part(n).y
                    cv2.circle(frame, (x, y), 2, (255, 0, 0), -1)
            
            # If no face is detected, update with default values
            if not faces:
                self.update_focus_data(False, False, "UNKNOWN")
                # Draw red focus indicator when no face detected
                cv2.rectangle(frame, (10, 10), (30, 30), (0, 0, 255), -1)
                cv2.putText(frame, "NO FACE DETECTED", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            # Add this before emitting the frame
            status_text = "TRACKING" if self.tracking else "NOT TRACKING"
            status_color = (0, 255, 0) if self.tracking else (0, 0, 255)
            cv2.putText(frame, status_text, (frame.shape[1] - 200, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
            
            # Emit the frame
            self.change_pixmap_signal.emit(frame)
        
        # Release resources
        cap.release()
    
    def pause(self):
        self.paused = True
    
    def resume(self):
        self.paused = False
    
    def reset(self):
        self.focus_data = {
            "focused": True,
            "direction": "CENTER",
            "blinking": False,
            "focus_duration": 0,
            "distraction_count": 0,
            "avg_distraction_time": 0
        }
        self.reset_eye_movement_data()
        self.tracking = False
        self.is_focused = True
        self.focus_start_time = QDateTime.currentDateTime()
        self.distraction_start_time = None
        self.distraction_periods = []
        self.gaze_ratio_history = []
        self.focus_data_signal.emit(self.focus_data)

    def stop(self):
        self.running = False
        self.wait()
    def track_gaze_changes(self, gaze_ratio):
        """Track changes in gaze ratio to detect saccades and fixations"""
        if not self.tracking:
            return
        
        current_time = QDateTime.currentDateTime()
        
        # Initialize data on first call
        if self.last_gaze_ratio is None:
            self.last_gaze_ratio = gaze_ratio
            self.fixation_start_time = current_time
            self.in_fixation = True
            return
        
        # Calculate change in gaze ratio
        ratio_change = abs(gaze_ratio - self.last_gaze_ratio)
        
        # Detect potential saccade (significant gaze change)
        if ratio_change > self.gaze_change_threshold:
            self.saccade_confirmation_count += 1
            
            # Only register a saccade if we have enough consecutive frames with significant change
            if self.saccade_confirmation_count >= self.saccade_confirmation_threshold:
                # Record the gaze ratio change as a saccade
                self.gaze_ratio_changes.append(ratio_change)
                
                # If we were in a fixation, record its duration if it meets minimum duration
                if self.in_fixation:
                    fixation_duration = self.fixation_start_time.secsTo(current_time)
                    if fixation_duration >= self.min_fixation_duration:
                        self.fixation_durations.append(fixation_duration)
                    
                # Start a new fixation
                self.fixation_start_time = current_time
                self.in_fixation = True
                
                # Reset confirmation counter
                self.saccade_confirmation_count = 0
        else:
            # Reset confirmation counter for stability
            self.saccade_confirmation_count = 0
        
        # Update last gaze ratio
        self.last_gaze_ratio = gaze_ratio

    def get_eye_movement_data(self):
        """Return the collected eye movement data"""
        return {
            'gaze_ratio_changes': self.gaze_ratio_changes.copy(),
            'fixation_durations': self.fixation_durations.copy()
        }

    def reset_eye_movement_data(self):
        """Reset all eye movement data"""
        self.gaze_ratio_changes = []
        self.fixation_durations = []
        self.last_gaze_ratio = None
        self.fixation_start_time = None
        self.in_fixation = False
        self.saccade_confirmation_count = 0 