from flask import Flask, request, jsonify,send_from_directory
from flask_cors import CORS
import mysql.connector
from datetime import datetime, timedelta
import cv2
import numpy as np
import logging
from twilio.rest import Client
import requests
from apscheduler.schedulers.background import BackgroundScheduler
import json
from werkzeug.security import generate_password_hash, check_password_hash
from bs4 import BeautifulSoup
import random
import PyPDF2
import docx
import os
import sqlite3
from werkzeug.utils import secure_filename
# Initialize Flask app
app = Flask(__name__, static_folder='static') 
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://username:password@hostname:3306/smart_classroom.sql'  # Update with your details
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
def initialize_database():
    if not os.path.exists(DATABASE_FILE):
        print("Initializing database...")
        conn = sqlite3.connect(DATABASE_FILE)
        with open(SQL_SCRIPT_FILE, "r") as f:
            conn.executescript(f.read())
        conn.close()
        print("Database initialized.")

# Serve the React app
@app.route('/')
def serve():
    return send_from_directory(app.static_folder, 'index.html')

# Serve static files for React
@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(app.static_folder, path)

# API Keys and Configuration
TWILIO_ACCOUNT_SID = 'ACae498339b89f6ed1d86f2c74ad569e39'
TWILIO_AUTH_TOKEN = 'da7749274c9e8fc63701903f871933c8'
TWILIO_PHONE_NUMBER = '+17856453727'
API_KEY = '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'

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'smart_classroom'
}

def get_db_connection():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise
@app.route('/attendance/mark-present', methods=['POST'])
def mark_student_present():
    try:
        data = request.json
        student_id = data.get('student_id')
        subject_id = data.get('subject_id')

        if not all([student_id, subject_id]):
            return jsonify({
                "status": "error",
                "message": "Student ID and Subject ID are required"
            }), 400

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        try:
            # First check if an attendance record exists for today
            cursor.execute("""
                SELECT id, status 
                FROM attendance 
                WHERE student_id = %s 
                AND subject_id = %s 
                AND date = CURDATE()
            """, (student_id, subject_id))
            
            existing_record = cursor.fetchone()
            
            if existing_record:
                # Update existing record
                cursor.execute("""
                    UPDATE attendance 
                    SET status = 1 
                    WHERE id = %s
                """, (existing_record['id'],))
            else:
                # Insert new record
                cursor.execute("""
                    INSERT INTO attendance 
                    (student_id, subject_id, date, status) 
                    VALUES (%s, %s, CURDATE(), 1)
                """, (student_id, subject_id))

            db.commit()

            # Verify the update
            cursor.execute("""
                SELECT status 
                FROM attendance 
                WHERE student_id = %s 
                AND subject_id = %s 
                AND date = CURDATE()
            """, (student_id, subject_id))
            
            updated_record = cursor.fetchone()
            
            if updated_record and updated_record['status'] == 1:
                return jsonify({
                    "status": "success",
                    "message": "Attendance marked successfully",
                    "data": {"is_present": True}
                })
            else:
                raise Exception("Failed to update attendance status")

        finally:
            cursor.close()
            db.close()

    except Exception as e:
        logger.error(f"Error marking attendance: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/student/recovery-assignments', methods=['GET'])
def get_recovery_assignments():
    try:
        student_id = request.args.get('student_id')
        if not student_id:
            return jsonify({"status": "error", "message": "Student ID is required"}), 400

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # Log the student ID being processed
        print(f"Fetching recovery assignments for student ID: {student_id}")

        # Check for consecutive absences in the last week for each subject
        cursor.execute("""
            WITH ConsecutiveAbsences AS (
                SELECT 
                    a.subject_id,
                    s.name as subject_name,
                    s.code as subject_code,
                    COUNT(*) as absent_count,
                    GROUP_CONCAT(a.date ORDER BY a.date) as absent_dates
                FROM attendance a
                JOIN subjects s ON a.subject_id = s.id
                WHERE a.student_id = %s 
                    AND a.status = 0 
                    AND a.date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                GROUP BY a.subject_id
                HAVING COUNT(*) >= 3
            )
            SELECT * FROM ConsecutiveAbsences
        """, (student_id,))
        
        absent_subjects = cursor.fetchall()
        print(f"Absent subjects: {absent_subjects}")

        # For each subject with consecutive absences, generate assignment if not exists
        for subject in absent_subjects:
            # Check if assignment already exists for this subject and student
            cursor.execute("""
                SELECT id FROM assignments 
                WHERE student_id = %s 
                AND subject_id = %s 
                AND created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            """, (student_id, subject['subject_id']))

            if not cursor.fetchone():
                # Generate dynamic open-ended questions using NVIDIA API
                prompt = f"""Generate 5 random questions about {subject['subject_name']}.
                Include a mix of:
                - Easy questions (basic understanding)
                - Medium questions (application-based)
                - Hard questions (analysis and problem-solving)

                Make each question different in difficulty and concept.
                Return only the questions, one per line."""

                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {API_KEY}"  # Ensure you have your API key set
                }

                payload = {
                    "model": "nvidia/llama-3.1-nemotron-70b-instruct",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a question generator specializing in creating easy open-ended educational questions."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 1.2,
                    "max_tokens": 1000  # Limit the response to ensure concise questions
                }
                
                response = requests.post(
                    "https://integrate.api.nvidia.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30
                )

                if response.status_code == 200:
                    response_data = response.json()
                    questions = response_data['choices'][0]['message']['content'].strip().split('\n')
                    questions = [q.strip() for q in questions if q.strip()]  # Clean up the questions

                    # Ensure only 5 questions are taken
                    questions = questions[:6]

                    # Insert new assignment
                    cursor.execute("""
                        INSERT INTO assignments 
                        (subject_id, student_id, title, description, due_date)
                        VALUES (%s, %s, %s, %s, DATE_ADD(CURDATE(), INTERVAL 7 DAY))
                    """, (
                        subject['subject_id'],
                        student_id,
                        f"Recovery Assignment - {subject['subject_name']}",
                        json.dumps(questions)
                    ))
                    db.commit()
                else:
                    print(f"Error generating questions: {response.text}")

        # Fetch all assignments for the student
        cursor.execute("""
            SELECT 
                a.id,
                a.title,
                a.description,
                a.due_date,
                s.name as subject_name,
                s.code as subject_code,
                COALESCE(sub.plagiarism_score, NULL) as plagiarism_score,
                CASE WHEN sub.id IS NOT NULL THEN TRUE ELSE FALSE END as is_submitted
            FROM assignments a
            JOIN subjects s ON a.subject_id = s.id
            LEFT JOIN assignment_submissions sub ON a.id = sub.assignment_id 
                AND sub.student_id = a.student_id
            WHERE a.student_id = %s
            ORDER BY a.due_date DESC
        """, (student_id,))

        assignments = cursor.fetchall()

        # Format assignments for frontend
        formatted_assignments = []
        for assignment in assignments:
            formatted_assignments.append({
                'id': assignment['id'],
                'title': assignment['title'],
                'subject_name': assignment['subject_name'],
                'subject_code': assignment['subject_code'],
                'due_date': assignment['due_date'].strftime('%Y-%m-%d'),
                'questions': json.loads(assignment['description']),
                'plagiarism_score': assignment['plagiarism_score'],
                'is_submitted': assignment['is_submitted']
            })

        return jsonify({
            "status": "success",
            "data": formatted_assignments
        })

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()
@app.route('/current-class', methods=['GET'])
def get_current_class_endpoint():
    try:
        student_id = request.args.get('student_id')
        if not student_id:
            return jsonify({
                "status": "error",
                "message": "Student ID is required"
            }), 400

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        
        # Get current day and time
        current_day = datetime.now().weekday() + 1  # 1=Monday, 7=Sunday
        current_time = datetime.now().strftime('%H:%M:%S')
        
        # Get current ongoing class with attendance status
        cursor.execute("""
            SELECT 
                s.id as subject_id,
                s.name as subject_name,
                s.code as subject_code,
                t.name as teacher_name,
                ss.start_time,
                ss.end_time,
                TIME_FORMAT(ss.start_time, '%h:%i %p') as formatted_start_time,
                TIME_FORMAT(ss.end_time, '%h:%i %p') as formatted_end_time,
                COALESCE(a.status, 0) as is_present
            FROM students st
            JOIN subjects s ON s.class_id = st.class_id
            JOIN teachers t ON s.teacher_id = t.id
            JOIN subject_schedule ss ON s.id = ss.subject_id
            LEFT JOIN attendance a ON a.subject_id = s.id 
                AND a.student_id = st.id 
                AND a.date = CURDATE()
            WHERE st.id = %s
                AND ss.day_of_week = %s
                AND %s BETWEEN ss.start_time AND ss.end_time
        """, (student_id, current_day, current_time))
        
        current_class = cursor.fetchone()
        
        if current_class:
            response_data = {
            "subject_id": current_class['subject_id'],
            "subject_name": current_class['subject_name'],
            "subject_code": current_class['subject_code'],
            "teacher_name": current_class['teacher_name'],
            "formatted_start_time": current_class['formatted_start_time'],
            "formatted_end_time": current_class['formatted_end_time'],
            "is_present": bool(current_class['is_present'])  # Ensure this is a boolean
        }
        
            return jsonify({
            "status": "success",
            "data": response_data
            })
        else:
            return jsonify({
                "status": "error",
                "message": "No ongoing class found"
            }), 404

    except Exception as e:
        logger.error(f"Error getting current class: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()

@app.route('/attendance/mark-present', methods=['POST'])
def mark_attendance():
    try:
        data = request.json
        student_id = data.get('student_id')
        class_id = data.get('class_id')

        if not all([student_id, class_id]):
            return jsonify({
                "status": "error",
                "message": "Student ID and Class ID are required"
            }), 400
        # Get current ongoing class
        current_class = get_current_class(class_id)
        if not current_class:
            return jsonify({
                "status": "error",
                "message": "No ongoing class found"
            }), 404

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # Check if attendance already exists
        cursor.execute("""
            SELECT id, status 
            FROM attendance 
            WHERE student_id = %s 
            AND subject_id = %s 
            AND date = CURRENT_DATE()
        """, (student_id, current_class['subject_id']))
        
        existing_attendance = cursor.fetchone()

        if existing_attendance:
            # Update existing attendance
            cursor.execute("""
                UPDATE attendance 
                SET status = 1 
                WHERE id = %s
            """, (existing_attendance['id'],))
        else:
            # Create new attendance record
            cursor.execute("""
                INSERT INTO attendance (student_id, subject_id, date, status)
                VALUES (%s, %s, CURRENT_DATE(), 1)
            """, (student_id, current_class['subject_id']))

        db.commit()
        cursor.close()
        db.close()

        return jsonify({
            "status": "success",
            "message": "Attendance marked successfully",
            "data": {
                "subject": current_class['subject_name'],
                "teacher": current_class['teacher_name'],
                "time": f"{current_class['formatted_start_time']} - {current_class['formatted_end_time']}"
            }
        })

    except Exception as e:
        logger.error(f"Error marking attendance: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
@app.route('/student/course-recommendations', methods=['GET'])
def get_course_recommendations():
    try:
        student_id = request.args.get('student_id')
        if not student_id:
            return jsonify({
                "status": "error",
                "message": "Student ID is required"
            }), 400

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # Get student's performance data
        cursor.execute("""
            SELECT 
                s.name as subject_name,
                s.code as subject_code,
                CAST(AVG((ia.marks_obtained/ia.total_marks) * 100) AS DECIMAL(5,2)) as percentage
            FROM internal_assessments ia
            JOIN subjects s ON ia.subject_id = s.id
            WHERE ia.student_id = %s
            GROUP BY s.name, s.code
        """, (student_id,))

        performance = cursor.fetchall()

        if not performance:
            return jsonify({
                "status": "error",
                "message": "No performance data found"
            }), 404

        recommendations = {}
        for subject in performance:
            percentage = float(subject['percentage']) if subject['percentage'] else 0
            subject_name = subject['subject_name']
            
            # Get courses based on performance level
            if percentage < 60:
                level = "Beginner"
                courses = get_beginner_courses(subject_name)
            elif percentage < 75:
                level = "Intermediate"
                courses = get_intermediate_courses(subject_name)
            else:
                level = "Advanced"
                courses = get_advanced_courses(subject_name)

            recommendations[subject_name] = {
                "performance": percentage,
                "level": level,
                "courses": courses
            }

        return jsonify({
            "status": "success",
            "data": {
                "recommendations": recommendations
            }
        })

    except Exception as e:
        logger.error(f"Error generating course recommendations: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

def get_beginner_courses(subject):
    courses = [
        {
            "title": f"Introduction to {subject}",
            "platform": "freeCodeCamp",
            "difficulty": "Beginner",
            "description": f"Learn the fundamentals of {subject} with hands-on practice",
            "url": f"https://www.freecodecamp.org/learn/{subject.lower().replace(' ', '-')}"
        },
        {
            "title": f"{subject} Basics",
            "platform": "W3Schools",
            "difficulty": "Beginner",
            "description": f"Step-by-step guide to {subject} fundamentals",
            "url": f"https://www.w3schools.com/{subject.lower().replace(' ', '')}"
        },
        {
            "title": f"Getting Started with {subject}",
            "platform": "MDN Web Docs",
            "difficulty": "Beginner",
            "description": f"Comprehensive guide to {subject} for beginners",
            "url": f"https://developer.mozilla.org/en-US/docs/Learn/{subject.lower().replace(' ', '_')}"
        }
    ]
    return courses

def get_intermediate_courses(subject):
    courses = [
        {
            "title": f"Intermediate {subject}",
            "platform": "edX",
            "difficulty": "Intermediate",
            "description": f"Deepen your understanding of {subject} concepts",
            "url": f"https://www.edx.org/learn/{subject.lower().replace(' ', '-')}"
        },
        {
            "title": f"Professional {subject} Development",
            "platform": "Codecademy",
            "difficulty": "Intermediate",
            "description": f"Build professional {subject} skills",
            "url": f"https://www.codecademy.com/learn/{subject.lower().replace(' ', '-')}"
        },
        {
            "title": f"{subject} in Practice",
            "platform": "GeeksforGeeks",
            "difficulty": "Intermediate",
            "description": f"Practice-oriented {subject} learning",
            "url": f"https://www.geeksforgeeks.org/{subject.lower().replace(' ', '-')}"
        }
    ]
    return courses

def get_advanced_courses(subject):
    courses = [
        {
            "title": f"Advanced {subject} Concepts",
            "platform": "MIT OpenCourseWare",
            "difficulty": "Advanced",
            "description": f"Master advanced {subject} topics",
            "url": f"https://ocw.mit.edu/search/?q={subject.lower().replace(' ', '+')}"
        },
        {
            "title": f"Expert {subject} Techniques",
            "platform": "Stanford Online",
            "difficulty": "Advanced",
            "description": f"Advanced {subject} methodologies and best practices",
            "url": f"https://online.stanford.edu/search-catalog?query={subject.lower().replace(' ', '+')}"
        },
        {
            "title": f"{subject} Mastery",
            "platform": "Khan Academy",
            "difficulty": "Advanced",
            "description": f"Complete mastery of {subject} concepts",
            "url": f"https://www.khanacademy.org/search?query={subject.lower().replace(' ', '+')}"
        }
    ]
    return courses
# Authentication Routes
# In final.py
def get_current_class(class_id):
    """
    Get details of the currently ongoing class for a given class_id
    """
    try:
        # Define days list at the start of the function
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # Print current time and day for debugging
        current_time = datetime.now().strftime('%I:%M %p')
        current_day = datetime.now().strftime('%A')
        current_weekday = datetime.now().weekday() + 1
        
        print("\n=== ONGOING CLASS DETAILS ===")
        print(f"Current Time: {current_time}")
        print(f"Current Day: {current_day}")
        print(f"Weekday Number: {current_weekday}")
        print(f"Class ID being checked: {class_id}")
        print("============================")

        cursor.execute("""
            SELECT 
                s.id as subject_id,
                s.name as subject_name,
                s.code as subject_code,
                t.name as teacher_name,
                t.id as teacher_id,
                TIME_FORMAT(ss.start_time, '%h:%i %p') as formatted_start_time,
                TIME_FORMAT(ss.end_time, '%h:%i %p') as formatted_end_time,
                ss.day_of_week
            FROM subject_schedule ss
            JOIN subjects s ON ss.subject_id = s.id
            LEFT JOIN teachers t ON s.teacher_id = t.id
            WHERE s.class_id = %s 
            AND ss.day_of_week = WEEKDAY(CURRENT_DATE()) + 1
            AND CURRENT_TIME() BETWEEN ss.start_time AND ss.end_time
            LIMIT 1
        """, (class_id,))
        
        class_info = cursor.fetchone()
        
        if class_info:
            # Add day name
            class_info['day_name'] = days[class_info['day_of_week'] - 1]

            print("\n=== FOUND CLASS DETAILS ===")
            print(f"Subject: {class_info['subject_name']} ({class_info['subject_code']})")
            print(f"Teacher: {class_info['teacher_name']}")
            print(f"Time: {class_info['formatted_start_time']} - {class_info['formatted_end_time']}")
            print(f"Day: {class_info['day_name']}")
            print("==========================\n")
        else:
            print("\n=== NO ONGOING CLASS FOUND ===")
            print("Checking database for schedule...")
            
            # Debug query to show all schedules for this class
            cursor.execute("""
                SELECT 
                    s.name as subject_name,
                    ss.day_of_week,
                    TIME_FORMAT(ss.start_time, '%h:%i %p') as formatted_start_time,
                    TIME_FORMAT(ss.end_time, '%h:%i %p') as formatted_end_time
                FROM subject_schedule ss
                JOIN subjects s ON ss.subject_id = s.id
                WHERE s.class_id = %s
                ORDER BY ss.day_of_week, ss.start_time
            """, (class_id,))
            
            all_schedules = cursor.fetchall()
            if all_schedules:
                print("\nAll scheduled classes for this class_id:")
                for schedule in all_schedules:
                    day_name = days[schedule['day_of_week'] - 1]
                    print(f"{schedule['subject_name']} on {day_name}: "
                          f"{schedule['formatted_start_time']} - {schedule['formatted_end_time']}")
            else:
                print("No schedule found for this class_id")
            print("============================\n")

        return class_info

    except Exception as e:
        print("\n=== ERROR OCCURRED ===")
        print(f"Error fetching current class: {e}")
        print("=====================\n")
        logger.error(f"Error fetching current class: {e}")
        return None
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()
get_current_class(1)
@app.route('/login', methods=['POST'])
def login():
    db = None
    cursor = None
    try:
        logger.debug(f"Received login request: {request.json}")
        
        data = request.json
        if not data:
            return jsonify({
                "status": "error",
                "message": "No data provided"
            }), 400

        email = data.get('email')
        password = data.get('password')  # Plain password from request
        role = data.get('role')

        if not all([email, password, role]):
            return jsonify({
                "status": "error",
                "message": "Email, password and role are required"
            }), 400

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # First get the hashed password from users table
        cursor.execute("""
            SELECT id, password FROM users 
            WHERE email = %s AND role = %s
        """, (email, role))
        
        user_auth = cursor.fetchone()
        
        if not user_auth or not check_password_hash(user_auth['password'], password):
            return jsonify({
                "status": "error",
                "message": "Invalid credentials"
            }), 401

        # If password is correct, get user details based on role
        if role == 'student':
            query = """
                SELECT 
                    u.id as user_id,
                    u.email,
                    u.role,
                    s.id as role_id,
                    s.name,
                    s.roll_number,
                    s.class_id
                FROM users u
                JOIN students s ON u.id = s.user_id
                WHERE u.id = %s
            """
        elif role == 'teacher':
             query = """
                SELECT 
                    u.id as user_id,
                    u.email,
                    u.role,
                    t.id as teacher_id,
                    t.name,
                    t.department
                FROM users u
                JOIN teachers t ON u.id = t.user_id
                WHERE u.id = %s
            """
        else:  # parent
            query = """
                SELECT 
                    u.id as user_id,
                    u.email,
                    u.role,
                    s.id as student_id,
                    s.name as student_name
                FROM users u
                JOIN students s ON s.parent_phone IS NOT NULL
                WHERE u.id = %s
            """

        cursor.execute(query, (user_auth['id'],))
        user = cursor.fetchone()

        if not user:
            return jsonify({
                "status": "error",
                "message": "User data not found"
            }), 404

        logger.info(f"Successful login for user: {email}")

        response_data = {
            "status": "success",
            "user": {
                "id": user['user_id'],
                "email": user['email'],
                "role": user['role']
            }
        }

        if role == 'student':
            response_data["user"].update({
                "role_id": user['role_id'],
                "name": user['name'],
                "roll_number": user['roll_number'],
                "class_id": user['class_id']
            })
        elif role == 'teacher':
            response_data["user"].update({
                "teacher_id": user['teacher_id'],  # Changed from role_id
                "name": user['name'],
                "department": user['department']
            })
        else:  # parent
            response_data["user"].update({
                "student_id": user['student_id'],
                "student_name": user['student_name']
            })

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({
            "status": "error",
            "message": "An error occurred during login"
        }), 500
    
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()
def generate_session_token(user_id):
    # In a real application, use a proper JWT implementation
    return f"session_{user_id}_{datetime.now().timestamp()}"

# Student Routes
# In final.py

@app.route('/student/attendance', methods=['GET'])
def get_student_attendance():
    try:
        student_id = request.args.get('student_id')
        if not student_id:
            return jsonify({
                "status": "error",
                "message": "Student ID is required"
            }), 400

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # Get attendance history with subject details
        cursor.execute("""
            SELECT 
                DATE_FORMAT(a.date, '%Y-%m-%d') as date,
                s.name as subject,
                a.status
            FROM attendance a
            JOIN subjects s ON a.subject_id = s.id
            WHERE a.student_id = %s
            ORDER BY a.date DESC
        """, (student_id,))

        attendance_records = cursor.fetchall()
        
        # Convert status to integer explicitly
        formatted_records = [{
            'date': record['date'],
            'subject': record['subject'],
            'status': int(record['status'])  # Ensure status is an integer
        } for record in attendance_records]

        return jsonify({
            "status": "success",
            "data": formatted_records
        })

    except Exception as e:
        logger.error(f"Error fetching attendance: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()
@app.route('/analyze-stream', methods=['POST'])
def analyze_stream():
    try:
        print("\n=== STARTING STREAM ANALYSIS ===")
        
        if 'image' not in request.files:
            print("No image provided in request")
            return jsonify({"status": "error", "message": "No image provided"}), 400

        file = request.files['image']
        student_id = request.form.get('student_id')
        inactivity_count = int(request.form.get('inactivity_count', 0))
        
        print(f"Student ID: {student_id}")
        print(f"Inactivity Count: {inactivity_count}")

        # Process image for activity detection
        npimg = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(npimg, cv2.COLOR_BGR2GRAY)

        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

        faces = face_cascade.detectMultiScale(img, 1.3, 5)
        is_active = False

        for (x, y, w, h) in faces:
            roi_gray = img[y:y+h, x:x+w]
            eyes = eye_cascade.detectMultiScale(roi_gray)
            if len(eyes) >= 2:
                is_active = True
                break

        print(f"Activity Detection Result: {'Active' if is_active else 'Inactive'}")
        
        notification_sent = False
        notification_message = ""

        # Send notification when count reaches 5
        if not is_active:
            print(f"Student inactive. Current count: {inactivity_count}")
        
        if not is_active and inactivity_count >= 5:
            print("\n=== INACTIVITY THRESHOLD REACHED ===")
            try:
                db = get_db_connection()
                cursor = db.cursor(dictionary=True)

                print("Getting student and mentor details...")
                # Get student and mentor details
                cursor.execute("""
                    SELECT 
                        s.name as student_name,
                        m.phone_number as mentor_phone,
                        m.name as mentor_name,
                        s.class_id
                    FROM students s
                    JOIN mentors m ON s.mentor_id = m.id
                    WHERE s.id = %s
                """, (student_id,))

                result = cursor.fetchone()
                
                if not result:
                    print(f"No student/mentor found for student_id: {student_id}")
                    logger.error(f"No student or mentor found for student_id: {student_id}")
                    return jsonify({
                        "status": "error",
                        "message": "Student or mentor not found"
                    }), 404

                print(f"Found student: {result['student_name']}")
                print(f"Mentor: {result['mentor_name']}")
                print(f"Mentor phone: {result['mentor_phone']}")

                if result['mentor_phone']:
                    # Get current class using the function
                    print("Getting current class information...")
                    current_class = get_current_class(result['class_id'])
                    
                    if current_class:
                        print(f"Current class found: {current_class['subject_name']}")
                        # Create detailed SMS message with class info
                        sms_message = (
                            f"STUDENT INACTIVITY ALERT!\n"
                            f"Student: {result['student_name']}\n"
                            f"Current Class: {current_class['subject_name']} ({current_class['subject_code']})\n"
                            f"Teacher: {current_class['teacher_name']}\n"
                            f"Class Time: {current_class['formatted_start_time']} - {current_class['formatted_end_time']}\n"
                            f"Alert Time: {datetime.now().strftime('%I:%M %p')}\n"
                            f"Status: Student has been inactive for 5 consecutive checks."
                        )
                    else:
                        print("No current class found")
                        # Fallback message if no class is scheduled
                        sms_message = (
                            f"STUDENT INACTIVITY ALERT!\n"
                            f"Student: {result['student_name']}\n"
                            f"Time: {datetime.now().strftime('%I:%M %p')}\n"
                            f"Status: Student has been inactive for 5 consecutive checks.\n"
                            f"Note: No scheduled class found at this time."
                        )

                    print("\n=== SENDING SMS NOTIFICATION ===")
                    print(f"To: {result['mentor_name']} ({result['mentor_phone']})")
                    print("Message Content:")
                    print("------------------------")
                    print(sms_message)
                    print("------------------------")

                    try:
                        # Send SMS using Twilio
                        message = twilio_client.messages.create(
                            from_=TWILIO_PHONE_NUMBER,
                            to=result['mentor_phone'],
                            body=sms_message
                        )
                        
                        notification_sent = True
                        notification_message = f"Alert SMS sent to mentor {result['mentor_name']}"
                        print(f"SMS sent successfully!")
                        print(f"Message SID: {message.sid}")
                        print("============================\n")
                        
                        logger.info(f"SMS sent successfully! Message SID: {message.sid}")

                        # Reset inactivity count after successful notification
                        print("Resetting inactivity count...")
                        cursor.execute("""
                            UPDATE students 
                            SET inactivity_count = 0, last_active = CURRENT_TIMESTAMP 
                            WHERE id = %s
                        """, (student_id,))
                        
                        db.commit()

                    except Exception as e:
                        print("\n=== SMS SENDING FAILED ===")
                        print(f"Error: {str(e)}")
                        print("========================\n")
                        logger.error(f"Failed to send SMS: {e}")
                        return jsonify({
                            "status": "error",
                            "message": f"Failed to send SMS: {str(e)}"
                        }), 500

            except Exception as e:
                print(f"\n=== DATABASE ERROR ===")
                print(f"Error: {str(e)}")
                print("====================\n")
                logger.error(f"Database error: {e}")
                return jsonify({
                    "status": "error",
                    "message": f"Database error: {str(e)}"
                }), 500
            finally:
                if 'cursor' in locals():
                    cursor.close()
                if 'db' in locals():
                    db.close()

        print("\n=== ANALYSIS COMPLETE ===")
        print(f"Is Active: {is_active}")
        print(f"Notification Sent: {notification_sent}")
        print("=======================\n")

        return jsonify({
            "status": "success",
            "expression": "active" if is_active else "inactive",
            "message": "Student is active" if is_active else "Inactivity detected",
            "notification_sent": notification_sent,
            "notification_message": notification_message,
            "should_reset": notification_sent
        })

    except Exception as e:
        print("\n=== STREAM ANALYSIS ERROR ===")
        print(f"Error: {str(e)}")
        print("===========================\n")
        logger.error(f"Stream analysis error: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
          

@app.route('/student/check-submission/<int:assignment_id>', methods=['GET'])
def check_submission(assignment_id):
    try:
        student_id = request.args.get('student_id')
        if not student_id:
            return jsonify({
                "status": "error",
                "message": "Student ID is required"
            }), 400

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # Check if submission exists
        cursor.execute("""
            SELECT id 
            FROM assignment_submissions 
            WHERE assignment_id = %s AND student_id = %s
        """, (assignment_id, student_id))
        
        submission = cursor.fetchone()
        
        return jsonify({
            "status": "success",
            "submitted": bool(submission)
        })

    except Exception as e:
        logger.error(f"Error checking submission: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()

# Assignment Routes
@app.route('/student/marks', methods=['GET'])
def get_student_marks():
    try:
        student_id = request.args.get('student_id')
        if not student_id:
            return jsonify({
                "status": "error",
                "message": "Student ID is required"
            }), 400

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                ia.id,
                s.name as subject_name,
                ia.assessment_type,
                ia.marks_obtained,
                ia.total_marks,
                ia.date
            FROM internal_assessments ia
            JOIN subjects s ON ia.subject_id = s.id
            WHERE ia.student_id = %s
            ORDER BY ia.date DESC
        """, (student_id,))

        marks = cursor.fetchall()
        
        return jsonify({
            "status": "success",
            "data": marks
        })

    except Exception as e:
        logger.error(f"Error fetching student marks: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()
@app.route('/student/assignments', methods=['GET'])
def get_student_assignments():
    try:
        student_id = request.args.get('student_id')
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT a.*, s.name as subject_name, 
                   COALESCE(sub.plagiarism_score, 0) as plagiarism_score,
                   sub.status as submission_status
            FROM assignments a
            JOIN subjects s ON a.subject_id = s.id
            LEFT JOIN assignment_submissions sub ON a.id = sub.assignment_id 
                AND sub.student_id = %s
            WHERE a.id IN (
                SELECT assignment_id FROM student_assignments 
                WHERE student_id = %s
            )
        """, (student_id, student_id))

        assignments = cursor.fetchall()
        return jsonify({"status": "success", "data": assignments})

    except Exception as e:
        logger.error(f"Error fetching assignments: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/student/submit-assignment', methods=['POST'])
def submit_assignment():
    try:
        if 'file' not in request.files:
            return jsonify({
                "status": "error",
                "message": "No file provided"
            }), 400

        file = request.files['file']
        student_id = request.form.get('student_id')
        assignment_id = request.form.get('assignment_id')

        if not all([student_id, assignment_id]):
            return jsonify({
                "status": "error",
                "message": "Missing required fields"
            }), 400

        # Validate file type
        allowed_extensions = {'.pdf', '.doc', '.docx'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({
                "status": "error",
                "message": "Invalid file type. Please upload PDF or DOC/DOCX files only."
            }), 400

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # Check for existing submission
        cursor.execute("""
            SELECT id FROM assignment_submissions 
            WHERE assignment_id = %s AND student_id = %s
        """, (assignment_id, student_id))
        
        if cursor.fetchone():
            return jsonify({
                "status": "error",
                "message": "Assignment already submitted"
            }), 400

        # Save file
        filename = secure_filename(f"{student_id}_{assignment_id}_{file.filename}")
        file_path = os.path.join('uploads', filename)
        file.save(file_path)

        try:
            # Save submission
            cursor.execute("""
                INSERT INTO assignment_submissions 
                (assignment_id, student_id, file_path, status)
                VALUES (%s, %s, %s, 'submitted')
            """, (assignment_id, student_id, file_path))

            # Update assignment status
            cursor.execute("""
                UPDATE assignments 
                SET status = 'completed'
                WHERE id = %s
            """, (assignment_id,))

            db.commit()

            return jsonify({
                "status": "success",
                "message": "Assignment submitted successfully"
            })

        except Exception as e:
            # Clean up file if processing fails
            if os.path.exists(file_path):
                os.remove(file_path)
            raise e

    except Exception as e:
        logger.error(f"Error submitting assignment: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()
def check_attendance():
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        current_time = datetime.now().time()
        current_date = datetime.now().date()

        print("\n=== CHECKING ATTENDANCE ===")
        print(f"Current Time: {current_time}")
        print(f"Current Date: {current_date}")
        print("=========================\n")

        # Get current subject schedule
        cursor.execute("""
            SELECT ss.*, s.name as subject_name, s.id as subject_id
            FROM subject_schedule ss
            JOIN subjects s ON ss.subject_id = s.id
            WHERE TIME(%s) BETWEEN ss.start_time AND ss.end_time
            AND ss.day_of_week = WEEKDAY(CURDATE()) + 1
        """, (current_time,))

        current_subjects = cursor.fetchall()

        if not current_subjects:
            logger.info("No subjects scheduled for current time")
            return

        for subject in current_subjects:
            print(f"\nChecking subject: {subject['subject_name']}")
            
            # Find students with 3 consecutive absences
            cursor.execute("""
                SELECT s.*, COUNT(*) as absent_count
                FROM students s
                JOIN attendance a ON s.id = a.student_id
                WHERE a.subject_id = %s 
                AND a.status = 0
                AND a.date >= DATE_SUB(%s, INTERVAL 3 DAY)
                GROUP BY s.id
                HAVING COUNT(*) >= 3
            """, (subject['subject_id'], current_date))

            absent_students = cursor.fetchall()

            print(f"Found {len(absent_students)} students with 3+ absences")

            for student in absent_students:
                print(f"Processing student: {student['name']}")
                send_absence_notifications(student, subject)

    except Exception as e:
        print("\n=== ATTENDANCE CHECK ERROR ===")
        print(f"Error: {str(e)}")
        print("============================\n")
        logger.error(f"Error in check_attendance: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(check_attendance, 'cron', 
    hour=21,     # Modify this hour as needed
    minute=50,  # Modify this minute as needed
)
scheduler.start()
# Notification Functions

def send_absence_notifications(student, subject):
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # Fetch student phone numbers from database
        cursor.execute("""
            SELECT student_phone, parent_phone 
            FROM students 
            WHERE id = %s
        """, (student['id'],))
        
        phone_numbers = cursor.fetchone()
        
        if not phone_numbers:
            logger.error(f"No phone numbers found for student ID: {student['id']}")
            return

        # Notification message
        message = (
            f"Absence Alert: {student['name']} has been absent in "
            f"{subject['subject_name']} for 3 consecutive days. "
            f"Time: {subject['start_time']} - {subject['end_time']}"
        )

        print("\n=== SENDING SMS NOTIFICATION ===")
        print(f"Student: {student['name']}")
        print(f"Message: {message}")
        print("===============================\n")

        # Send SMS using Twilio
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        # Send to student if phone number exists
        if phone_numbers['student_phone']:
            try:
                client.messages.create(
                    body=message,
                    from_=TWILIO_PHONE_NUMBER,
                    to=phone_numbers['student_phone']
                )
                logger.info(f"SMS sent to student: {phone_numbers['student_phone']}")
            except Exception as e:
                logger.error(f"Failed to send SMS to student: {e}")

        # Send to parent if phone number exists
        if phone_numbers['parent_phone']:
            try:
                client.messages.create(
                    body=message,
                    from_=TWILIO_PHONE_NUMBER,
                    to=phone_numbers['parent_phone']
                )
                logger.info(f"SMS sent to parent: {phone_numbers['parent_phone']}")
            except Exception as e:
                logger.error(f"Failed to send SMS to parent: {e}")

    except Exception as e:
        logger.error(f"Error in send_absence_notifications: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()

if __name__ == '__main__':
    initialize_database()  # Ensure the database is set up before starting the app
    app.run(host='0.0.0.0', port=5000)
