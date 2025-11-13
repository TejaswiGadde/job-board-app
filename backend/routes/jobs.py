# backend/routes/jobs.py
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from ..app import db
from ..models import Job, Employer
from datetime import datetime

jobs_bp = Blueprint('jobs', __name__, url_prefix='/jobs')

@jobs_bp.route('/employer/post_job', methods=['GET', 'POST'])
@login_required
def post_job():
    # Only allow Employer users
    if not isinstance(current_user, Employer):
        return jsonify(success=False, message="Only employers can post jobs"), 403

    if request.method == 'POST':
        try:
            job = Job(
                title=request.form['title'],
                description=request.form['description'],
                location=request.form['location'],
                salary=request.form.get('salary'),  # Can be empty
                category=request.form['category'],
                employer_id=current_user.id,
                posted_at=datetime.utcnow()
            )
            db.session.add(job)
            db.session.commit()
            return jsonify(success=True, message="Job posted successfully!")
        except Exception as e:
            db.session.rollback()
            return jsonify(success=False, message=str(e)), 400

    return render_template('employer_post_job.html')

@jobs_bp.route('/api/jobs')
def api_jobs():
    jobs = Job.query.all()
    return jsonify([{
        'id': j.id,
        'title': j.title,
        'description': j.description,
        'location': j.location,
        'salary': j.salary,
        'category': j.category,
        'company': j.employer.company if j.employer else "Unknown",
        'posted_at': j.posted_at.isoformat() if hasattr(j, 'posted_at') else None
    } for j in jobs])

@jobs_bp.route('/employer/my_jobs')
@login_required
def my_jobs():
    # Only allow Employer users
    if not isinstance(current_user, Employer):
        return "Access denied: Employers only", 403

    jobs = Job.query.filter_by(employer_id=current_user.id).all()
    return jsonify([{
        'id': j.id,
        'title': j.title,
        'description': j.description,
        'location': j.location,
        'salary': j.salary,
        'category': j.category,
        'posted_at': j.posted_at.isoformat() if hasattr(j, 'posted_at') else None
    } for j in jobs])