# backend/app.py
import os
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, send_from_directory
)
from werkzeug.security import generate_password_hash, check_password_hash
from .models import db, Admin, Employer, JobSeeker, Job, Application


def create_app():

    # -------------------------------
    #   PROJECT ROOT PATHS
    # -------------------------------
    PROJECT_ROOT = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )

    DB_PATH = os.path.join(PROJECT_ROOT, "job_board.db")
    TEMPLATE_PATH = os.path.join(PROJECT_ROOT, "templates")
    STATIC_PATH = os.path.join(PROJECT_ROOT, "static")
    UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, "uploads")

    print("----------------------------------------------------")
    print("PROJECT ROOT:", PROJECT_ROOT)
    print("DB PATH:", DB_PATH)
    print("TEMPLATES:", TEMPLATE_PATH)
    print("STATIC:", STATIC_PATH)
    print("UPLOAD FOLDER:", UPLOAD_FOLDER)
    print("DB EXISTS?", os.path.exists(DB_PATH))
    print("----------------------------------------------------")

    # -------------------------------
    #   FLASK APP SETUP
    # -------------------------------
    app = Flask(
        __name__,
        template_folder=TEMPLATE_PATH,
        static_folder=STATIC_PATH
    )

    app.config["SECRET_KEY"] = "change-me"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + DB_PATH
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    db.init_app(app)

    # -------------------------------
    #   LOGIN REQUIRED DECORATOR
    # -------------------------------
    def login_required(role=None):
        def decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                if "user_id" not in session:
                    flash("Please log in first.", "warning")
                    return redirect(url_for("login"))
                if role and session.get("role") != role:
                    flash("Not authorized.", "danger")
                    return redirect(url_for("index"))
                return f(*args, **kwargs)
            return wrapper
        return decorator

    # -------------------------------
    #   CREATE TABLES + DEFAULT ADMIN
    # -------------------------------
    with app.app_context():
        db.create_all()

        if not Admin.query.filter_by(username="admin").first():
            admin = Admin(
                username="admin",
                password=generate_password_hash("admin123")
            )
            db.session.add(admin)
            db.session.commit()
            print("Default admin created: admin / admin123")

    # -------------------------------
    #   HOME
    # -------------------------------
    @app.route("/")
    def index():
        jobs = Job.query.order_by(Job.id.desc()).limit(5).all()
        return render_template("index.html", jobs=jobs)

    # -------------------------------
    #   JOB LISTINGS
    # -------------------------------
    @app.route("/job-listings")
    def job_listings():
        q = request.args.get("q", "")
        category = request.args.get("category", "")
        location = request.args.get("location", "")

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
            "job_listings.html",
            jobs=jobs,
            q=q,
            category=category,
            location=location
        )

    # -------------------------------
    #   REGISTER
    # -------------------------------
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":

            role = request.form.get("role")
            name = request.form.get("name")
            email = request.form.get("email")
            password = request.form.get("password")
            company = request.form.get("company", "")

            import re
            pattern = r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$"
            if not re.match(pattern, password):
                flash("Password must be 8+ chars incl. letter, number & special char.", "danger")
                return redirect(url_for("register"))

            if role == "employer":
                if Employer.query.filter_by(email=email).first():
                    flash("Employer email already registered.", "danger")
                    return redirect(url_for("register"))

                emp = Employer(
                    name=name,
                    email=email,
                    password=generate_password_hash(password),
                    company=company
                )
                db.session.add(emp)

            elif role == "seeker":
                if JobSeeker.query.filter_by(email=email).first():
                    flash("Job seeker email already registered.", "danger")
                    return redirect(url_for("register"))

                resume_file = request.files.get("resume_file")
                resume_filename = None

                if resume_file:
                    resume_filename = resume_file.filename
                    resume_path = os.path.join(UPLOAD_FOLDER, resume_filename)
                    resume_file.save(resume_path)

                seeker = JobSeeker(
                    name=name,
                    email=email,
                    password=generate_password_hash(password),
                    resume=resume_filename
                )
                db.session.add(seeker)

            else:
                flash("Choose employer or seeker.", "danger")
                return redirect(url_for("register"))

            db.session.commit()
            flash("Registration successful!", "success")
            return redirect(url_for("login"))

        return render_template("register.html")

    # -------------------------------
    #   LOGIN
    # -------------------------------
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            role = request.form.get("role")
            email_or_username = request.form.get("email")
            password = request.form.get("password")

            user = None

            if role == "seeker":
                user = JobSeeker.query.filter_by(email=email_or_username).first()
            elif role == "employer":
                user = Employer.query.filter_by(email=email_or_username).first()
            elif role == "admin":
                user = Admin.query.filter_by(username=email_or_username).first()

            if user and check_password_hash(user.password, password):
                session["user_id"] = user.id
                session["role"] = role
                flash("Logged in!", "success")

                if role == "admin":
                    return redirect(url_for("admin_dashboard"))
                if role == "employer":
                    return redirect(url_for("employer_jobs"))
                return redirect(url_for("job_listings"))

            flash("Invalid credentials.", "danger")
            return redirect(url_for("login"))

        return render_template("login.html")

    # -------------------------------
    #   LOGOUT
    # -------------------------------
    @app.route("/logout")
    def logout():
        session.clear()
        flash("Logged out.", "info")
        return redirect(url_for("index"))

    # -------------------------------
    #   APPLY TO JOB
    # -------------------------------
    @app.route("/apply/<int:job_id>", methods=["POST"])
    @login_required(role="seeker")
    def apply(job_id):
        job = Job.query.get_or_404(job_id)
        seeker_id = session["user_id"]

        if Application.query.filter_by(job_id=job.id, seeker_id=seeker_id).first():
            flash("Already applied!", "warning")
            return redirect(url_for("job_listings"))

        app_obj = Application(
            job_id=job_id,
            seeker_id=seeker_id,
            status="Applied"
        )
        db.session.add(app_obj)
        db.session.commit()

        flash("Application submitted!", "success")
        return redirect(url_for("my_applications"))

    @app.route("/my-applications")
    @login_required(role="seeker")
    def my_applications():
        seeker_id = session["user_id"]
        applications = (
            Application.query.filter_by(seeker_id=seeker_id)
            .join(Job)
            .add_entity(Job)
            .all()
        )
        return render_template("my_applications.html", applications=applications)

    # -------------------------------
    #   EMPLOYER JOBS
    # -------------------------------
    @app.route("/employer/jobs")
    @login_required(role="employer")
    def employer_jobs():
        employer_id = session["user_id"]
        jobs = Job.query.filter_by(employer_id=employer_id).all()
        return render_template("employer_jobs.html", jobs=jobs)

    @app.route("/employer/post-job", methods=["GET", "POST"])
    @login_required(role="employer")
    def employer_post_job():
        if request.method == "POST":
            employer_id = session["user_id"]
            title = request.form.get("title")
            description = request.form.get("description")
            location = request.form.get("location")
            salary_raw = request.form.get("salary")
            category = request.form.get("category")

            try:
                salary = float(salary_raw) if salary_raw else None
            except:
                flash("Salary must be a number.", "danger")
                return redirect(url_for("employer_post_job"))

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

            flash("Job posted!", "success")
            return redirect(url_for("employer_jobs"))

        return render_template("employer_post_job.html")

    @app.route("/employer/edit-job/<int:job_id>", methods=["GET", "POST"])
    @login_required(role="employer")
    def edit_job(job_id):
        employer_id = session["user_id"]
        job = Job.query.get_or_404(job_id)

        if job.employer_id != employer_id:
            flash("Unauthorized.", "danger")
            return redirect(url_for("employer_jobs"))

        if request.method == "POST":
            job.title = request.form.get("title")
            job.description = request.form.get("description")
            job.location = request.form.get("location")
            job.category = request.form.get("category")

            salary_raw = request.form.get("salary")
            try:
                job.salary = float(salary_raw) if salary_raw else None
            except:
                flash("Salary must be numeric.", "danger")
                return redirect(url_for("edit_job", job_id=job.id))

            db.session.commit()
            flash("Job updated!", "success")
            return redirect(url_for("employer_jobs"))

        return render_template("edit_jobs.html", job=job)

    # -------------------------------
    #   DELETE JOB
    # -------------------------------
    @app.route("/employer/delete-job/<int:job_id>", methods=["POST"])
    @login_required(role="employer")
    def delete_job(job_id):
        employer_id = session["user_id"]
        job = Job.query.get_or_404(job_id)

        if job.employer_id != employer_id:
            flash("Unauthorized.", "danger")
            return redirect(url_for("employer_jobs"))

        Application.query.filter_by(job_id=job.id).delete()
        db.session.delete(job)
        db.session.commit()

        flash("Job deleted.", "info")
        return redirect(url_for("employer_jobs"))

    # -------------------------------
    #   SERVE UPLOADED RESUME FILES
    # -------------------------------
    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    # -------------------------------
    #   UPDATE APPLICATION STATUS
    # -------------------------------
    @app.route("/employer/application/<int:application_id>/update", methods=["POST"])
    @login_required(role="employer")
    def update_application_status(application_id):
        app_obj = Application.query.get_or_404(application_id)

        job = Job.query.get(app_obj.job_id)
        if job.employer_id != session["user_id"]:
            flash("Unauthorized.", "danger")
            return redirect(url_for("employer_jobs"))

        new_status = request.form.get("status")
        app_obj.status = new_status
        db.session.commit()

        flash("Application status updated.", "success")
        return redirect(url_for("employer_view_applications", job_id=app_obj.job_id))

    # -------------------------------
    #   EMPLOYER VIEW APPLICATIONS
    # -------------------------------
    @app.route("/employer/job/<int:job_id>/applications")
    @login_required(role="employer")
    def employer_view_applications(job_id):
        job = Job.query.get_or_404(job_id)

        if job.employer_id != session["user_id"]:
            flash("Unauthorized.", "danger")
            return redirect(url_for("employer_jobs"))

        applications = (
            Application.query.filter_by(job_id=job_id)
            .join(JobSeeker)
            .add_entity(JobSeeker)
            .all()
        )

        return render_template(
            "employer_view_applications.html",
            job=job,
            applications=applications
        )

    # -------------------------------
    #   ADMIN DASHBOARD
    # -------------------------------
    @app.route("/admin/dashboard")
    @login_required(role="admin")
    def admin_dashboard():
        employers = Employer.query.all()
        seekers = JobSeeker.query.all()
        jobs = Job.query.all()
        applications = Application.query.all()

        stats = {
            "employer_count": len(employers),
            "seeker_count": len(seekers),
            "job_count": len(jobs),
            "application_count": len(applications),
        }

        return render_template(
            "admin_dashboard.html",
            stats=stats,
            employers=employers,
            seekers=seekers,
            jobs=jobs,
            applications=applications
        )

    # -------------------------------
    #   FINAL RETURN
    # -------------------------------
    return app
