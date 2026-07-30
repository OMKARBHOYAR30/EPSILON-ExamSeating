-- EPSILON | Exam Seating Arrangement System
-- SQLite Schema DDL

PRAGMA foreign_keys = ON;

-- ============================================================
-- USERS
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name     TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'Admin',
    created_at    TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ============================================================
-- CLASSROOMS
-- ============================================================
CREATE TABLE IF NOT EXISTS classrooms (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    block              TEXT NOT NULL,
    room_no            TEXT UNIQUE NOT NULL,
    default_capacity   INTEGER NOT NULL,
    default_rows       INTEGER NOT NULL,
    default_row_layout TEXT NOT NULL,
    created_at         TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ============================================================
-- SECTION STUDENTS (College Master Roll Lists)
-- Handles dropped/left student roll number gaps cleanly
-- ============================================================
CREATE TABLE IF NOT EXISTS section_students (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    college       TEXT NOT NULL DEFAULT 'GHRCE',
    program       TEXT NOT NULL DEFAULT 'B.Tech',
    branch        TEXT NOT NULL,
    semester      TEXT NOT NULL,
    section       TEXT NOT NULL,
    roll_no       TEXT NOT NULL,
    student_name  TEXT DEFAULT '',
    is_active     INTEGER NOT NULL DEFAULT 1
);

-- ============================================================
-- ALLOCATIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS allocations (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    room_no            TEXT NOT NULL,
    block              TEXT NOT NULL,
    used_capacity      INTEGER NOT NULL,
    rows               INTEGER NOT NULL,
    row_layout         TEXT NOT NULL,
    bench_mode         TEXT NOT NULL DEFAULT 'DOUBLE', -- 'DOUBLE' / 'SINGLE'
    exam_date          TEXT NOT NULL DEFAULT (date('now')), -- Manual Exam Date
    academic_year      TEXT NOT NULL DEFAULT '2026-2027', -- Academic Year
    exam_name          TEXT NOT NULL DEFAULT 'CAE-I',     -- Exam Name / Type
    
    -- Left Group
    left_college       TEXT NOT NULL,
    left_program       TEXT,
    left_branch        TEXT NOT NULL,
    left_semester      TEXT NOT NULL,
    left_section       TEXT NOT NULL,
    left_roll_prefix   TEXT DEFAULT '',
    left_roll_from     INTEGER DEFAULT 0,
    left_roll_to       INTEGER DEFAULT 0,
    left_entry_mode    TEXT DEFAULT 'auto', -- 'auto' / 'manual' / 'dataset'
    
    -- Right Group
    right_college      TEXT DEFAULT '',
    right_program      TEXT DEFAULT '',
    right_branch       TEXT DEFAULT '',
    right_semester     TEXT DEFAULT '',
    right_section      TEXT DEFAULT '',
    right_roll_prefix  TEXT DEFAULT '',
    right_roll_from    INTEGER DEFAULT 0,
    right_roll_to      INTEGER DEFAULT 0,
    right_entry_mode   TEXT DEFAULT 'auto', -- 'auto' / 'manual' / 'dataset'
    
    created_at         TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ============================================================
-- SEATING CHART
-- ============================================================
CREATE TABLE IF NOT EXISTS seating_chart (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    allocation_id INTEGER NOT NULL REFERENCES allocations(id) ON DELETE CASCADE,
    bench_no      INTEGER NOT NULL,
    left_student  TEXT DEFAULT '',
    right_student TEXT DEFAULT '',
    room_no       TEXT NOT NULL
);

-- ============================================================
-- MANUAL ROLLS
-- ============================================================
CREATE TABLE IF NOT EXISTS manual_rolls (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    allocation_id INTEGER NOT NULL REFERENCES allocations(id) ON DELETE CASCADE,
    side          TEXT NOT NULL, -- 'LEFT' / 'RIGHT'
    roll_no       TEXT NOT NULL
);

-- ============================================================
-- INDEXES FOR HIGH-PERFORMANCE SEARCH & DUPLICATE CHECKS
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_section_students_sec ON section_students(college, branch, semester, section, is_active);
CREATE INDEX IF NOT EXISTS idx_section_students_roll ON section_students(roll_no);
CREATE INDEX IF NOT EXISTS idx_allocations_date ON allocations(exam_date, room_no);
CREATE INDEX IF NOT EXISTS idx_seating_chart_alloc ON seating_chart(allocation_id);
CREATE INDEX IF NOT EXISTS idx_seating_chart_left ON seating_chart(left_student);
CREATE INDEX IF NOT EXISTS idx_seating_chart_right ON seating_chart(right_student);
CREATE INDEX IF NOT EXISTS idx_manual_rolls_alloc ON manual_rolls(allocation_id, roll_no);
