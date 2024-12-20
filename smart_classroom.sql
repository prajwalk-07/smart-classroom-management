CREATE DATABASE IF NOT EXISTS smart_classroom;
USE smart_classroom;

-- Users table
DROP TABLE IF EXISTS users;
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role TEXT CHECK(role IN ('student', 'teacher', 'parent')) NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Mentors table
DROP TABLE IF EXISTS mentors;
CREATE TABLE mentors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    department TEXT
);

-- Students table
DROP TABLE IF EXISTS students;
CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    roll_number TEXT NOT NULL UNIQUE,
    class_id INTEGER,
    mentor_id INTEGER,
    student_phone TEXT,
    parent_phone TEXT,
    inactivity_count INTEGER DEFAULT 0,
    last_active TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (mentor_id) REFERENCES mentors(id) ON DELETE SET NULL
);

-- Teachers table
DROP TABLE IF EXISTS teachers;
CREATE TABLE teachers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    department TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Subjects table
DROP TABLE IF EXISTS subjects;
CREATE TABLE subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    code TEXT NOT NULL UNIQUE,
    teacher_id INTEGER,
    class_id INTEGER,
    FOREIGN KEY (teacher_id) REFERENCES teachers(id)
);

-- Attendance table
DROP TABLE IF EXISTS attendance;
CREATE TABLE attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    subject_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    status INTEGER DEFAULT 0, -- Use 0 for false, 1 for true
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX unique_attendance ON attendance (student_id, subject_id, date);

-- Assignments table
DROP TABLE IF EXISTS assignments;
CREATE TABLE assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    due_date TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    status TEXT CHECK(status IN ('pending', 'completed')) DEFAULT 'pending',
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);

-- Assignment Submissions table
DROP TABLE IF EXISTS assignment_submissions;
CREATE TABLE assignment_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assignment_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    submission_date TEXT DEFAULT CURRENT_TIMESTAMP,
    status TEXT CHECK(status IN ('pending', 'reviewed')) DEFAULT 'pending',
    FOREIGN KEY (assignment_id) REFERENCES assignments(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX unique_submission ON assignment_submissions (assignment_id, student_id);

-- Internal Assessments table
DROP TABLE IF EXISTS internal_assessments;
CREATE TABLE internal_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    subject_id INTEGER NOT NULL,
    assessment_type TEXT,
    marks_obtained REAL,
    total_marks REAL,
    date TEXT NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);

-- Subject Schedule table
DROP TABLE IF EXISTS subject_schedule;
CREATE TABLE subject_schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL, -- 1=Monday, 2=Tuesday, etc.
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    FOREIGN KEY (subject_id) REFERENCES subjects(id)
);

-- Subject Topics table
DROP TABLE IF EXISTS subject_topics;
CREATE TABLE subject_topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL,
    topic_name TEXT NOT NULL,
    description TEXT,
    FOREIGN KEY (subject_id) REFERENCES subjects(id)
);

