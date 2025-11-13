# backend/routes/admin.py
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from ..models import Employer, JobSeeker, Job, Application, Admin  # ← Admin added

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    # Only allow authenticated Admin instances
    if not isinstance(current_user, Admin):
        return "Access denied: Admins only", 403

    stats = {
        'employers': Employer.query.count(),
        'seekers': JobSeeker.query.count(),
        'jobs': Job.query.count(),
        'applications': Application.query.count()
    }

    return render_template('admin_dashboard.html', **stats)