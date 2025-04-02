import sqlite3
import os
import json
from datetime import datetime

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
            
            self.conn.commit()
            print("Database initialized successfully")
        except sqlite3.Error as e:
            print(f"Database initialization error: {e}")
    
    # Replace the save_session method in database_manager.py with this improved version

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
            try:
                import json
                focus_data_json = json.dumps(session_data['focus_data'])
                print(f"Successfully serialized focus_data: {len(focus_data_json)} characters")
            except Exception as e:
                print(f"Error serializing focus_data: {e}")
                # Create a simplified version of focus_data
                simplified_data = []
                for item in session_data['focus_data']:
                    # Convert non-serializable objects to strings
                    simplified_item = {}
                    for k, v in item.items():
                        if k == 'timestamp':
                            simplified_item[k] = v.isoformat()
                        else:
                            simplified_item[k] = v
                    simplified_data.append(simplified_item)
                focus_data_json = json.dumps(simplified_data)
                print(f"Used simplified focus_data: {len(focus_data_json)} characters")
            
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
            
            # Final commit
            self.conn.commit()
            print(f"Session saved successfully with ID: {session_id}")
            return session_id
        
        except Exception as e:
            import traceback
            print(f"Error saving session: {e}")
            traceback.print_exc()
            try:
                self.conn.rollback()
            except:
                pass
            return None
    
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
            return session
        
        except sqlite3.Error as e:
            print(f"Error retrieving session details: {e}")
            return None
    
    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
            print("Database connection closed")