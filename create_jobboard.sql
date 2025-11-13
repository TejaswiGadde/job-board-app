-- create_jobboard.sql
PRAGMA foreign_keys = ON;

-- Employer
CREATE TABLE IF NOT EXISTS employer (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    password VARCHAR(200) NOT NULL,
    company VARCHAR(100)
);

-- Job Seeker
CREATE TABLE IF NOT EXISTS job_seeker (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    password VARCHAR(200) NOT NULL,
    resume VARCHAR(200)
);

-- Admin
CREATE TABLE IF NOT EXISTS admin (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(200) NOT NULL
);

-- Job
CREATE TABLE IF NOT EXISTS job (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    location VARCHAR(100),
    salary REAL,
    category VARCHAR(100),
    employer_id INTEGER NOT NULL,
    FOREIGN KEY (employer_id) REFERENCES employer(id) ON DELETE CASCADE
);

-- Application
CREATE TABLE IF NOT EXISTS application (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    seeker_id INTEGER NOT NULL,
    status VARCHAR(50) DEFAULT 'Applied',
    FOREIGN KEY (job_id) REFERENCES job(id) ON DELETE CASCADE,
    FOREIGN KEY (seeker_id) REFERENCES job_seeker(id) ON DELETE CASCADE,
    UNIQUE(job_id, seeker_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_job_employer ON job(employer_id);
CREATE INDEX IF NOT EXISTS idx_application_job ON application(job_id);
CREATE INDEX IF NOT EXISTS idx_application_seeker ON application(seeker_id);