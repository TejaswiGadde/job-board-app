# backend/routes/applications.py
from flask import Blueprint, jsonify, current_app
from flask_login import login_required, current_user
from ..app import db
from ..models import Application, Job, JobSeeker

applications_bp = Blueprint('applications', __name__, url_prefix='/applications')

@applications_bp.route('/apply/<int:job_id>', methods=['POST'])
@login_required
def apply(job_id):
    # Only allow JobSeeker users
    if not isinstance(current_user, JobSeeker):
        return jsonify(success=False, message="Only job seekers can apply"), 403

    # Check if already applied
    existing = Application.query.filter_by(
        job_id=job_id,
        seeker_id=current_user.id
    ).first()

    if existing:
        return jsonify(success=False, message="You have already applied for this job")

    # Create new application
    application = Application(job_id=job_id, seeker_id=current_user.id, status="Applied")
    db.session.add(application)
    db.session.commit()

    return jsonify(success=True, message="Application submitted successfully!")

@applications_bp.route('/my_applications')
@login_required
def my_applications():
    # Only allow JobSeeker users
    if not isinstance(current_user, JobSeeker):
        return "Access denied: Job seekers only", 403

    # Fetch all applications for current user
    apps = Application.query.filter_by(seeker_id=current_user.id).all()

    return jsonify([{
        'id': a.id,
        'job_id': a.job_id,
        'title': a.job.title if a.job else "Job Deleted",
        'company': a.job.employer.company if a.job and a.job.employer else "N/A",
        'status': a.status,
        'applied_at': a.applied_at.isoformat() if hasattr(a, 'applied_at') else None
    } for a in apps])