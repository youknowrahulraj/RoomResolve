import os
import uuid
from functools import wraps

from flask            import (Flask, render_template, redirect, url_for,
                               flash, session, request, abort)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils    import secure_filename

from config  import Config
from models  import db, User, Complaint
from forms   import (RegistrationForm, LoginForm, AdminLoginForm,
                     ComplaintForm, UpdateStatusForm)

# ── Application factory ───────────────────────────────────────────────────────
app = Flask(__name__)
app.config.from_object(Config)

# Bind SQLAlchemy to this app
db.init_app(app)

# Flask-WTF (CSRF) is auto-enabled via SECRET_KEY + WTF_CSRF_ENABLED=True
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)


# ── Helper: allowed file extensions ──────────────────────────────────────────
def allowed_file(filename: str) -> bool:
    """Return True only if the filename has a permitted image extension."""
    return ('.' in filename and
            filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS'])


# ── Auth decorators ───────────────────────────────────────────────────────────
def login_required(f):
    """Redirect to student login if no session exists."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Restrict route to admin users only."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


def student_required(f):
    """Restrict route to student users only."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'student':
            flash('Student access required.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# ── Database initialisation + default admin seed ─────────────────────────────
def init_db():
    """Create all tables and seed the default admin account."""
    db.create_all()

    # Create default admin if not already present
    admin_email = 'admin@roomresolve.com'
    if not User.query.filter_by(email=admin_email).first():
        admin = User(
            name          = 'Administrator',
            email         = admin_email,
            password_hash = generate_password_hash('admin123'),
            role          = 'admin',
        )
        db.session.add(admin)
        db.session.commit()
        print('[RoomResolve] Default admin created → admin@roomresolve.com / admin123')

    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    """Landing / home page."""
    return render_template('index.html')


# ── Student Registration ──────────────────────────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
def register():
    # Already logged-in students go straight to dashboard
    if session.get('role') == 'student':
        return redirect(url_for('student_dashboard'))

    form = RegistrationForm()
    if form.validate_on_submit():
        # Check duplicate email
        if User.query.filter_by(email=form.email.data.lower()).first():
            flash('An account with that email already exists.', 'danger')
            return render_template('register.html', form=form)

        user = User(
            name          = form.name.data.strip(),
            email         = form.email.data.lower().strip(),
            password_hash = generate_password_hash(form.password.data),
            hostel        = form.hostel.data.strip(),
            room          = form.room.data.strip(),
            role          = 'student',
        )
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


# ── Student Login ─────────────────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('role') == 'student':
        return redirect(url_for('student_dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and user.role == 'student' and check_password_hash(user.password_hash, form.password.data):
            # Store minimal info in session
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['role'] = 'student'
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(url_for('student_dashboard'))
        flash('Invalid email or password.', 'danger')

    return render_template('login.html', form=form)


# ── Logout ────────────────────────────────────────────────────────────────────
@app.route('/logout')
def logout():
    role = session.get('role')
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('admin_login') if role == 'admin' else url_for('login'))


# ══════════════════════════════════════════════════════════════════════════════
#  STUDENT ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/dashboard')
@login_required
@student_required
def student_dashboard():
    """Student dashboard with complaint statistics."""
    user = User.query.get_or_404(session['user_id'])
    complaints = Complaint.query.filter_by(user_id=user.id).all()

    stats = {
        'total':       len(complaints),
        'pending':     sum(1 for c in complaints if c.status == 'Pending'),
        'in_progress': sum(1 for c in complaints if c.status == 'In Progress'),
        'resolved':    sum(1 for c in complaints if c.status == 'Resolved'),
    }
    # Show the 5 most recent complaints on the dashboard
    recent = sorted(complaints, key=lambda c: c.created_at, reverse=True)[:5]

    return render_template('student_dashboard.html', user=user, stats=stats, recent=recent)


@app.route('/submit-complaint', methods=['GET', 'POST'])
@login_required
@student_required
def submit_complaint():
    """Allow a student to submit a new complaint with an optional image."""
    form = ComplaintForm()
    if form.validate_on_submit():
        image_filename = None

        # Handle optional image upload
        if form.image.data and form.image.data.filename:
            file = form.image.data
            if allowed_file(file.filename):
                # Generate a unique filename to prevent collisions
                ext  = file.filename.rsplit('.', 1)[1].lower()
                safe = f"{uuid.uuid4().hex}.{ext}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], safe))
                image_filename = safe
            else:
                flash('Invalid file type. Only images are allowed.', 'danger')
                return render_template('submit_complaint.html', form=form)

        complaint = Complaint(
            user_id        = session['user_id'],
            category       = form.category.data,
            description    = form.description.data.strip(),
            image_filename = image_filename,
            status         = 'Pending',
        )
        db.session.add(complaint)
        db.session.commit()
        flash('Your complaint has been submitted successfully!', 'success')
        return redirect(url_for('complaint_history'))

    return render_template('submit_complaint.html', form=form)


@app.route('/complaint-history')
@login_required
@student_required
def complaint_history():
    """Display all complaints submitted by the logged-in student."""
    complaints = (Complaint.query
                  .filter_by(user_id=session['user_id'])
                  .order_by(Complaint.created_at.desc())
                  .all())
    return render_template('complaint_history.html', complaints=complaints)


# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))

    form = AdminLoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower(), role='admin').first()
        if user and check_password_hash(user.password_hash, form.password.data):
            session['user_id']   = user.id
            session['user_name'] = user.name
            session['role']      = 'admin'
            flash('Welcome, Admin!', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('Invalid admin credentials.', 'danger')

    return render_template('admin_login.html', form=form)


@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Admin dashboard with full complaint management."""
    # Global statistics
    total       = Complaint.query.count()
    pending     = Complaint.query.filter_by(status='Pending').count()
    in_progress = Complaint.query.filter_by(status='In Progress').count()
    resolved    = Complaint.query.filter_by(status='Resolved').count()

    # All complaints with their student info, newest first
    complaints = (Complaint.query
                  .join(User, Complaint.user_id == User.id)
                  .order_by(Complaint.created_at.desc())
                  .all())

    status_form = UpdateStatusForm()
    return render_template('admin_dashboard.html',
                           total=total, pending=pending,
                           in_progress=in_progress, resolved=resolved,
                           complaints=complaints, status_form=status_form)


@app.route('/admin/update-status/<int:complaint_id>', methods=['POST'])
@admin_required
def update_status(complaint_id):
    """Update the status of a specific complaint."""
    complaint = Complaint.query.get_or_404(complaint_id)
    form = UpdateStatusForm()
    if form.validate_on_submit():
        complaint.status = form.status.data
        db.session.commit()
        flash(f'Complaint #{complaint_id} status updated to "{complaint.status}".', 'success')
    else:
        flash('Invalid status value.', 'danger')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/delete-complaint/<int:complaint_id>', methods=['POST'])
@admin_required
def delete_complaint(complaint_id):
    """Delete a complaint and its associated image."""
    complaint = Complaint.query.get_or_404(complaint_id)

    # Remove uploaded image file if it exists
    if complaint.image_filename:
        img_path = os.path.join(app.config['UPLOAD_FOLDER'], complaint.image_filename)
        if os.path.exists(img_path):
            os.remove(img_path)

    db.session.delete(complaint)
    db.session.commit()
    flash(f'Complaint #{complaint_id} has been deleted.', 'info')
    return redirect(url_for('admin_dashboard'))


# ══════════════════════════════════════════════════════════════════════════════
#  ERROR HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

@app.errorhandler(404)
def page_not_found(e):
    return render_template('base.html',
                           error_code=404,
                           error_msg='Page not found.'), 404


@app.errorhandler(403)
def forbidden(e):
    return render_template('base.html',
                           error_code=403,
                           error_msg='Access forbidden.'), 403


@app.errorhandler(413)
def file_too_large(e):
    flash('File is too large. Maximum allowed size is 5 MB.', 'danger')
    return redirect(request.referrer or url_for('student_dashboard'))


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True)