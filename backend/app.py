# backend/app.py
import os
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session
)
from werkzeug.security import generate_password_hash, check_password_hash

from .models import db, Admin, Employer, JobSeeker, Job, Application


def create_app():
    base_dir = os.path.dirname(os.path.dirname(__file__))

    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, 'templates'),
        static_folder=os.path.join(base_dir, 'static'),
    )

    app.config['SECRET_KEY'] = 'change-me'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(
        base_dir, 'job_board.db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    # ---------- auth helper ----------
    def login_required(role=None):
        def decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                if 'user_id' not in session or 'role' not in session:
                    flash('Please log in first.', 'warning')
                    return redirect(url_for('login'))
                if role and session['role'] != role:
                    flash('You are not authorized for that page.', 'danger')
                    return redirect(url_for('index'))
                return f(*args, **kwargs)
            return wrapper
        return decorator

    # ---------- DB setup ----------
    with app.app_context():
        db.create_all()
        if not Admin.query.filter_by(username='admin').first():
            admin = Admin(
                username='admin',
                password=generate_password_hash('admin123')
            )
            db.session.add(admin)
            db.session.commit()

    # ---------- Public ----------
    @app.route('/')
    def index():
        jobs = Job.query.order_by(Job.id.desc()).limit(5).all()
        return render_template('index.html', jobs=jobs)

    @app.route('/job-listings')
    def job_listings():
        q = request.args.get('q', '').strip()
        category = request.args.get('category', '').strip()
        location = request.args.get('location', '').strip()

        query = Job.query

        if q:
            like = f"%{q}%"
            query = query.filter(
                Job.title.ilike(like) | Job.description.ilike(like)
            )
        if category:
            query = query.filter(Job.category.ilike(f"%{category}%"))
        if location:
            query = query.filter(Job.location.ilike(f"%{location}%"))

        jobs = query.order_by(Job.id.desc()).all()
        return render_template(
            'job_listings.html',
            jobs=jobs,
            q=q,
            category=category,
            location=location
        )

    # ---------- Auth ----------
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            role = request.form.get('role')   # 'seeker' or 'employer'
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            company = request.form.get('company', '')
            # For simplicity: resume as text (file upload skipped)
            resume = request.form.get('resume_text', '')

            if role not in ('seeker', 'employer'):
                flash('Please select Employer or Job Seeker.', 'danger')
                return redirect(url_for('register'))

            if not name or not email or not password:
                flash('Name, email and password are required.', 'danger')
                return redirect(url_for('register'))

            if role == 'employer':
                if Employer.query.filter_by(email=email).first():
                    flash('Employer email already registered.', 'danger')
                    return redirect(url_for('register'))
                emp = Employer(
                    name=name,
                    email=email,
                    password=generate_password_hash(password),
                    company=company
                )
                db.session.add(emp)
            else:
                if JobSeeker.query.filter_by(email=email).first():
                    flash('Job seeker email already registered.', 'danger')
                    return redirect(url_for('register'))
                seeker = JobSeeker(
                    name=name,
                    email=email,
                    password=generate_password_hash(password),
                    resume=resume
                )
                db.session.add(seeker)

            db.session.commit()
            flash('Registration successful. Please log in.', 'success')
            return redirect(url_for('login'))

        return render_template('register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            role = request.form.get('role')  # 'seeker', 'employer', 'admin'
            email_or_username = request.form.get('email')
            password = request.form.get('password')

            # 🔍 DEBUG PRINTS — WILL SHOW EXACT VALUES RECEIVED
            print("DEBUG ROLE RECEIVED:", role)
            print("DEBUG USERNAME RECEIVED:", email_or_username)

            user = None

            if role == 'seeker':
                user = JobSeeker.query.filter_by(email=email_or_username).first()
            elif role == 'employer':
                user = Employer.query.filter_by(email=email_or_username).first()
            elif role == 'admin':
                user = Admin.query.filter_by(username=email_or_username).first()
            else:
                flash('Invalid role selected.', 'danger')
                return redirect(url_for('login'))

            # Password check
            if user and check_password_hash(user.password, password):
                session.clear()
                session['user_id'] = user.id
                session['role'] = role
                flash('Logged in successfully.', 'success')

                if role == 'admin':
                    return redirect(url_for('admin_dashboard'))
                elif role == 'employer':
                    return redirect(url_for('employer_jobs'))
                else:
                    return redirect(url_for('job_listings'))

            flash('Invalid credentials.', 'danger')
            return redirect(url_for('login'))

        return render_template('login.html')

    @app.route('/logout')
    def logout():
        session.clear()
        flash('Logged out.', 'info')
        return redirect(url_for('index'))

    # ---------- Job seeker ----------
    @app.route('/apply/<int:job_id>', methods=['POST'])
    @login_required(role='seeker')
    def apply(job_id):
        job = Job.query.get_or_404(job_id)
        seeker_id = session['user_id']

        existing = Application.query.filter_by(
            job_id=job.id, seeker_id=seeker_id
        ).first()
        if existing:
            flash('You already applied for this job.', 'warning')
            return redirect(url_for('job_listings'))

        app_obj = Application(job_id=job.id, seeker_id=seeker_id, status='Applied')
        db.session.add(app_obj)
        db.session.commit()
        flash('Application submitted.', 'success')
        return redirect(url_for('my_applications'))

    @app.route('/my-applications')
    @login_required(role='seeker')
    def my_applications():
        seeker_id = session['user_id']
        applications = (
            Application.query
            .filter_by(seeker_id=seeker_id)
            .join(Job)
            .add_entity(Job)
            .all()
        )
        return render_template('my_applications.html', applications=applications)

    # ---------- Employer ----------
    @app.route('/employer/jobs')
    @login_required(role='employer')
    def employer_jobs():
        employer_id = session['user_id']
        jobs = Job.query.filter_by(employer_id=employer_id).all()
        return render_template('employer_jobs.html', jobs=jobs)

    @app.route('/employer/post-job', methods=['GET', 'POST'])
    @login_required(role='employer')
    def employer_post_job():
        if request.method == 'POST':
            employer_id = session['user_id']
            title = request.form.get('title')
            description = request.form.get('description')
            location = request.form.get('location')
            salary_raw = request.form.get('salary')
            category = request.form.get('category')

            if not title:
                flash('Title is required.', 'danger')
                return redirect(url_for('employer_post_job'))

            try:
                salary = float(salary_raw) if salary_raw else None
            except ValueError:
                flash('Salary must be a number.', 'danger')
                return redirect(url_for('employer_post_job'))

            job = Job(
                title=title,
                description=description,
                location=location,
                salary=salary,
                category=category,
                employer_id=employer_id
            )
            db.session.add(job)
            db.session.commit()
            flash('Job posted.', 'success')
            return redirect(url_for('employer_jobs'))

        return render_template('employer_post_job.html')

    @app.route('/employer/edit-job/<int:job_id>', methods=['GET', 'POST'])
    @login_required(role='employer')
    def edit_job(job_id):
        employer_id = session['user_id']
        job = Job.query.get_or_404(job_id)

        if job.employer_id != employer_id:
            flash('You can edit only your own jobs.', 'danger')
            return redirect(url_for('employer_jobs'))

        if request.method == 'POST':
            job.title = request.form.get('title')
            job.description = request.form.get('description')
            job.location = request.form.get('location')
            job.category = request.form.get('category')
            salary_raw = request.form.get('salary')

            try:
                job.salary = float(salary_raw) if salary_raw else None
            except ValueError:
                flash('Salary must be a number.', 'danger')
                return redirect(url_for('edit_job', job_id=job.id))

            db.session.commit()
            flash('Job updated.', 'success')
            return redirect(url_for('employer_jobs'))

        return render_template('edit_jobs.html', job=job)

    @app.route('/employer/delete-job/<int:job_id>', methods=['POST'])
    @login_required(role='employer')
    def delete_job(job_id):
        employer_id = session['user_id']
        job = Job.query.get_or_404(job_id)

        if job.employer_id != employer_id:
            flash('You can delete only your own jobs.', 'danger')
            return redirect(url_for('employer_jobs'))

        Application.query.filter_by(job_id=job.id).delete()
        db.session.delete(job)
        db.session.commit()
        flash('Job deleted.', 'info')
        return redirect(url_for('employer_jobs'))

    @app.route('/employer/view-applications/<int:job_id>')
    @login_required(role='employer')
    def employer_view_applications(job_id):
        employer_id = session['user_id']
        job = Job.query.get_or_404(job_id)

        if job.employer_id != employer_id:
            flash('Unauthorized.', 'danger')
            return redirect(url_for('employer_jobs'))

        applications = (
            Application.query
            .filter_by(job_id=job.id)
            .join(JobSeeker)
            .add_entity(JobSeeker)
            .all()
        )
        return render_template(
            'employer_view_applications.html',
            job=job,
            applications=applications
        )

    @app.route('/employer/update-application/<int:application_id>', methods=['POST'])
    @login_required(role='employer')
    def update_application_status(application_id):
        employer_id = session['user_id']
        application = Application.query.get_or_404(application_id)
        job = application.job

        if job.employer_id != employer_id:
            flash('Unauthorized.', 'danger')
            return redirect(url_for('employer_jobs'))

        new_status = request.form.get('status', 'Under Review')
        application.status = new_status
        db.session.commit()
        flash('Application status updated.', 'success')
        return redirect(url_for('employer_view_applications', job_id=job.id))

    # ---------- Admin ----------
    @app.route('/admin/dashboard')
    @login_required(role='admin')
    def admin_dashboard():
        employers = Employer.query.all()
        seekers = JobSeeker.query.all()
        jobs = Job.query.all()
        applications = Application.query.all()

        stats = {
            'employer_count': len(employers),
            'seeker_count': len(seekers),
            'job_count': len(jobs),
            'application_count': len(applications),
        }

        return render_template(
            'admin_dashboard.html',
            stats=stats,
            employers=employers,
            seekers=seekers,
            jobs=jobs,
            applications=applications
        )

    return app
