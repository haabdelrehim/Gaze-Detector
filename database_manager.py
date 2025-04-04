import sqlite3
import os
import json
from datetime import datetime
import traceback

class DatabaseManager:
    def __init__(self, db_path='focus_sessions.db'):
        """Initialize the database manager with the specified database path"""
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.initialize_database()
    
    def initialize_database(self):
        """Create the database and tables if they don't exist"""
        try:
            # Connect to the database
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            
            # Create sessions table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                duration INTEGER NOT NULL,
                distraction_count INTEGER NOT NULL,
                avg_distraction_time REAL NOT NULL,
                focus_percentage REAL NOT NULL,
                longest_focus_period INTEGER NOT NULL,
                focus_data TEXT NOT NULL
            )
            ''')
            
            # Create focus_points table for storing time-series data
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS focus_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                is_focused INTEGER NOT NULL,
                gaze_direction TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions (id)
            )
            ''')
            
            # Create eye_movement_data table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS eye_movement_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                gaze_ratio_changes TEXT NOT NULL,
                fixation_durations TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions (id)
            )
            ''')
            
            self.conn.commit()
            print("Database initialized successfully")
        except sqlite3.Error as e:
            print(f"Database initialization error: {e}")
    
    def save_session(self, session_data):
        """
        Save a completed session to the database
        
        Args:
            session_data (dict): Dictionary containing session information
        
        Returns:
            int: ID of the inserted session
        """
        try:
            # Convert datetime objects to strings
            start_time = session_data['start_time'].isoformat()
            end_time = session_data['end_time'].isoformat()
            
            # Convert focus_data to JSON string - handle potential serialization issues
            focus_data_json = self._serialize_data(session_data['focus_data'], 'focus_data')
            
            # Print values for debugging
            print(f"Saving session with values:")
            print(f"  start_time: {start_time}")
            print(f"  end_time: {end_time}")
            print(f"  duration: {session_data['duration']}")
            print(f"  distraction_count: {session_data['distraction_count']}")
            print(f"  avg_distraction_time: {session_data['avg_distraction_time']}")
            print(f"  focus_percentage: {session_data['focus_percentage']}")
            print(f"  longest_focus_period: {session_data['longest_focus_period']}")
            
            # Insert into sessions table with parameter binding
            sql = '''
            INSERT INTO sessions (
                start_time, end_time, duration, distraction_count, 
                avg_distraction_time, focus_percentage, longest_focus_period, focus_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            params = (
                start_time, end_time, 
                int(session_data['duration']),
                int(session_data['distraction_count']), 
                float(session_data['avg_distraction_time']),
                float(session_data['focus_percentage']), 
                int(session_data['longest_focus_period']),
                focus_data_json
            )
            
            # Print parameter sizes for debugging
            print(f"Parameter sizes:")
            print(f"  start_time: {len(start_time)} chars")
            print(f"  end_time: {len(end_time)} chars") 
            print(f"  focus_data_json: {len(focus_data_json)} chars")
            
            # Execute the SQL with parameters
            self.cursor.execute(sql, params)
            
            # Get the ID of the inserted session
            session_id = self.cursor.lastrowid
            print(f"Inserted session with ID: {session_id}")
            
            # Process focus points and eye movement data in a single transaction
            try:
                # Insert focus points - do this in smaller batches to avoid transaction issues
                focus_points = session_data['focus_points']
                print(f"Inserting {len(focus_points)} focus points")
                
                BATCH_SIZE = 50
                total_points = len(focus_points)
                
                for i in range(0, total_points, BATCH_SIZE):
                    batch = focus_points[i:i+BATCH_SIZE]
                    print(f"Processing batch {i//BATCH_SIZE + 1}/{(total_points + BATCH_SIZE - 1)//BATCH_SIZE}: {len(batch)} points")
                    
                    for point in batch:
                        timestamp = point['timestamp'].isoformat()
                        is_focused = 1 if point['is_focused'] else 0
                        
                        try:
                            self.cursor.execute('''
                            INSERT INTO focus_points (
                                session_id, timestamp, is_focused, gaze_direction
                            ) VALUES (?, ?, ?, ?)
                            ''', (
                                session_id, timestamp, is_focused, point['gaze_direction']
                            ))
                        except Exception as e:
                            print(f"Error inserting focus point: {e}")
                            print(f"Point data: timestamp={timestamp}, is_focused={is_focused}, direction={point['gaze_direction']}")
                    
                    # Commit each batch to avoid large transactions
                    self.conn.commit()
                    print(f"Committed batch {i//BATCH_SIZE + 1}")
                
                # Save eye movement data if available
                if 'eye_movement_data' in session_data and session_data['eye_movement_data']:
                    self._save_eye_movement_data(session_id, session_data['eye_movement_data'])
                else:
                    print("No eye movement data found in session_data")
                
                # Final commit
                self.conn.commit()
                print(f"Session saved successfully with ID: {session_id}")
                return session_id
                
            except Exception as e:
                print(f"Error saving focus points or eye movement data: {e}")
                traceback.print_exc()
                self.conn.rollback()
                # Continue with returning session_id even if points failed to save
                return session_id
        
        except Exception as e:
            print(f"Error saving session: {e}")
            traceback.print_exc()
            try:
                self.conn.rollback()
            except:
                pass
            return None

    def _serialize_data(self, data, data_name):
        """Helper function to serialize data to JSON with proper error handling"""
        try:
            json_data = json.dumps(data)
            print(f"Successfully serialized {data_name}: {len(json_data)} characters")
            return json_data
        except Exception as e:
            print(f"Error serializing {data_name}: {e}")
            # Create a simplified version for serialization
            simplified_data = []
            for item in data:
                # Convert non-serializable objects to strings
                simplified_item = {}
                for k, v in item.items():
                    if isinstance(v, datetime):
                        simplified_item[k] = v.isoformat()
                    else:
                        simplified_item[k] = v
                simplified_data.append(simplified_item)
            json_data = json.dumps(simplified_data)
            print(f"Used simplified {data_name}: {len(json_data)} characters")
            return json_data

    def _save_eye_movement_data(self, session_id, eye_movement_data):
        """Helper function to save eye movement data with proper error handling"""
        try:
            # Verify the structure of eye_movement_data
            if not isinstance(eye_movement_data, dict):
                print(f"Warning: eye_movement_data is not a dictionary, got {type(eye_movement_data)}")
                return False
            
            # Check for required keys
            required_keys = ['gaze_ratio_changes', 'fixation_durations']
            for key in required_keys:
                if key not in eye_movement_data:
                    print(f"Warning: Missing required key '{key}' in eye_movement_data")
                    return False
            
            # Serialize the data
            gaze_ratio_changes = json.dumps(eye_movement_data['gaze_ratio_changes'])
            fixation_durations = json.dumps(eye_movement_data['fixation_durations'])
            
            print(f"Saving eye movement data:")
            print(f"  - Gaze ratio changes: {len(eye_movement_data['gaze_ratio_changes'])} entries, {len(gaze_ratio_changes)} chars")
            print(f"  - Fixation durations: {len(eye_movement_data['fixation_durations'])} entries, {len(fixation_durations)} chars")
            
            # Insert the data
            self.cursor.execute('''
            INSERT INTO eye_movement_data (
                session_id, gaze_ratio_changes, fixation_durations
            ) VALUES (?, ?, ?)
            ''', (
                session_id, gaze_ratio_changes, fixation_durations
            ))
            
            self.conn.commit()
            print(f"Saved eye movement data for session {session_id}")
            return True
            
        except Exception as e:
            print(f"Error saving eye movement data: {e}")
            traceback.print_exc()
            return False
    
    def get_all_sessions(self):
        """Get all sessions from the database, ordered by start time descending"""
        try:
            self.cursor.execute('''
            SELECT id, start_time, end_time, duration, distraction_count, 
                   avg_distraction_time, focus_percentage, longest_focus_period
            FROM sessions
            ORDER BY start_time DESC
            ''')
            
            sessions = []
            for row in self.cursor.fetchall():
                sessions.append({
                    'id': row[0],
                    'start_time': datetime.fromisoformat(row[1]),
                    'end_time': datetime.fromisoformat(row[2]),
                    'duration': row[3],
                    'distraction_count': row[4],
                    'avg_distraction_time': row[5],
                    'focus_percentage': row[6],
                    'longest_focus_period': row[7]
                })
            
            return sessions
        
        except sqlite3.Error as e:
            print(f"Error retrieving sessions: {e}")
            return []
    
    def get_session_details(self, session_id):
        """Get detailed information for a specific session"""
        try:
            # Get session data
            self.cursor.execute('''
            SELECT id, start_time, end_time, duration, distraction_count, 
                   avg_distraction_time, focus_percentage, longest_focus_period, focus_data
            FROM sessions
            WHERE id = ?
            ''', (session_id,))
            
            row = self.cursor.fetchone()
            if not row:
                return None
            
            session = {
                'id': row[0],
                'start_time': datetime.fromisoformat(row[1]),
                'end_time': datetime.fromisoformat(row[2]),
                'duration': row[3],
                'distraction_count': row[4],
                'avg_distraction_time': row[5],
                'focus_percentage': row[6],
                'longest_focus_period': row[7],
                'focus_data': json.loads(row[8])
            }
            
            # Get focus points
            self.cursor.execute('''
            SELECT timestamp, is_focused, gaze_direction
            FROM focus_points
            WHERE session_id = ?
            ORDER BY timestamp
            ''', (session_id,))
            
            focus_points = []
            for row in self.cursor.fetchall():
                focus_points.append({
                    'timestamp': datetime.fromisoformat(row[0]),
                    'is_focused': bool(row[1]),
                    'gaze_direction': row[2]
                })
            
            session['focus_points'] = focus_points
            
            # Get eye movement data if available
            try:
                self.cursor.execute('''
                SELECT gaze_ratio_changes, fixation_durations
                FROM eye_movement_data
                WHERE session_id = ?
                ''', (session_id,))
                
                eye_data = self.cursor.fetchone()
                if eye_data:
                    session['eye_movement_data'] = {
                        'gaze_ratio_changes': json.loads(eye_data[0]),
                        'fixation_durations': json.loads(eye_data[1])
                    }
                    print(f"Retrieved eye movement data for session {session_id}")
                else:
                    print(f"No eye movement data found for session {session_id}")
            except sqlite3.Error as e:
                print(f"Error retrieving eye movement data: {e}")
            
            return session
        
        except sqlite3.Error as e:
            print(f"Error retrieving session details: {e}")
            return None
    
    def check_eye_movement_data(self, session_id):
        """Check if eye movement data exists for a given session"""
        try:
            self.cursor.execute('''
            SELECT COUNT(*) FROM eye_movement_data WHERE session_id = ?
            ''', (session_id,))
            
            count = self.cursor.fetchone()[0]
            
            if count > 0:
                # Get the data to inspect it
                self.cursor.execute('''
                SELECT gaze_ratio_changes, fixation_durations
                FROM eye_movement_data
                WHERE session_id = ?
                ''', (session_id,))
                
                data = self.cursor.fetchone()
                gaze_changes = json.loads(data[0])
                fixations = json.loads(data[1])
                
                print(f"=== Eye Movement Data for Session {session_id} ===")
                print(f"Gaze changes: {len(gaze_changes)} entries")
                print(f"Fixations: {len(fixations)} entries")
                print(f"Sample gaze changes: {gaze_changes[:5]}")
                print(f"Sample fixations: {fixations[:5]}")
                print("=== End of Eye Movement Data ===")
                
                return True
            else:
                print(f"No eye movement data found for session {session_id}")
                return False
            
        except sqlite3.Error as e:
            print(f"Error checking eye movement data: {e}")
            return False
        
    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
            print("Database connection closed")