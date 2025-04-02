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
            
            # Convert focus_data to JSON string
            focus_data_json = json.dumps(session_data['focus_data'])
            
            # Insert into sessions table
            self.cursor.execute('''
            INSERT INTO sessions (
                start_time, end_time, duration, distraction_count, 
                avg_distraction_time, focus_percentage, longest_focus_period, focus_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                start_time, end_time, session_data['duration'],
                session_data['distraction_count'], session_data['avg_distraction_time'],
                session_data['focus_percentage'], session_data['longest_focus_period'],
                focus_data_json
            ))
            
            # Get the ID of the inserted session
            session_id = self.cursor.lastrowid
            
            # Insert focus points
            for point in session_data['focus_points']:
                timestamp = point['timestamp'].isoformat()
                is_focused = 1 if point['is_focused'] else 0
                
                self.cursor.execute('''
                INSERT INTO focus_points (
                    session_id, timestamp, is_focused, gaze_direction
                ) VALUES (?, ?, ?, ?)
                ''', (
                    session_id, timestamp, is_focused, point['gaze_direction']
                ))
            
            self.conn.commit()
            print(f"Session saved with ID: {session_id}")
            return session_id
        
        except sqlite3.Error as e:
            print(f"Error saving session: {e}")
            self.conn.rollback()
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