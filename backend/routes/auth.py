# backend/routes/auth.py
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import login_user, logout_user, login_required, current_user
from ..app import db
from ..models import Employer, JobSeeker, Admin
import os

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Configure upload folder
UPLOAD_FOLDER = 'uploads/resumes'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ------------------------------------------------------------------
# REGISTER
# ------------------------------------------------------------------
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')

    try:
        role = request.form.get('role')
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        company = request.form.get('company', '')

        if not all([role, name, email, password]):
            return jsonify(success=False, message="All fields are required."), 400

        # Check for existing user
        existing = {
            'employer': Employer.query.filter_by(email=email).first(),
            'jobseeker': JobSeeker.query.filter_by(email=email).first(),
            'admin': Admin.query.filter_by(email=email).first()
        }

        if existing.get(role):
            return jsonify(success=False, message=f"{role.capitalize()} with this email already exists."), 400

        hashed_password = generate_password_hash(password)

        # Create user
        if role == 'employer':
            user = Employer(name=name, email=email, password=hashed_password, company=company)
        elif role == 'admin':
            user = Admin(name=name, email=email, password=hashed_password)
        else:  # jobseeker
            user = JobSeeker(name=name, email=email, password=hashed_password)

        db.session.add(user)
        db.session.flush()  # Get user.id before commit

        # Handle resume upload
        if role == 'jobseeker' and 'resume' in request.files:
            file = request.files['resume']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{user.id}_{file.filename}")
                upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                os.makedirs(os.path.dirname(upload_path), exist_ok=True)
                file.save(upload_path)
                user.resume = filename

        db.session.commit()

        return jsonify(
            success=True,
            message="Registration successful. Please log in.",
            redirect=url_for('auth.login')
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Registration error: {e}")
        return jsonify(success=False, message="Registration failed."), 500


# ------------------------------------------------------------------
# LOGIN
# ------------------------------------------------------------------
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    try:
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        if not all([email, password, role]):
            return jsonify(success=False, message="Email, password, and role are required."), 400

        # Map role to model
        model_map = {
            'employer': Employer,
            'jobseeker': JobSeeker,
            'admin': Admin
        }
        Model = model_map.get(role)
        if not Model:
            return jsonify(success=False, message="Invalid role."), 400

        user = Model.query.filter_by(email=email).first()

        # Critical: Check is_active + password
        if user and user.is_active and check_password_hash(user.password, password):
            login_user(user, remember=True)
            next_page = request.args.get('next') or url_for('main.index')
            return jsonify(
                success=True,
                message="Login successful.",
                user_id=user.get_id(),
                role=role,
                redirect=next_page
            )
        else:
            return jsonify(success=False, message="Invalid credentials or account inactive."), 401

    except Exception as e:
        current_app.logger.error(f"Login error: {e}")
        return jsonify(success=False, message="Login failed."), 500


# ------------------------------------------------------------------
# LOGOUT
# ------------------------------------------------------------------
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))