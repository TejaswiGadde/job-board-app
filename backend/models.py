# backend/models.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Admin(db.Model):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


class Employer(db.Model):
    __tablename__ = 'employer'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(100))

    jobs = db.relationship('Job', back_populates='employer', lazy=True)


class JobSeeker(db.Model):
    __tablename__ = 'job_seeker'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    resume = db.Column(db.String(200))

    applications = db.relationship('Application', back_populates='seeker', lazy=True)


class Job(db.Model):
    __tablename__ = 'job'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(100))
    salary = db.Column(db.Float)
    category = db.Column(db.String(100))
    employer_id = db.Column(db.Integer, db.ForeignKey('employer.id'), nullable=False)

    employer = db.relationship('Employer', back_populates='jobs', lazy=True)
    applications = db.relationship('Application', back_populates='job', lazy=True)


class Application(db.Model):
    __tablename__ = 'application'
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    seeker_id = db.Column(db.Integer, db.ForeignKey('job_seeker.id'), nullable=False)
    status = db.Column(db.String(50), default='Applied')

    job = db.relationship('Job', back_populates='applications', lazy=True)
    seeker = db.relationship('JobSeeker', back_populates='applications', lazy=True)
