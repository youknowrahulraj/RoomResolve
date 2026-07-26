from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy (bound to app in app.py)
db = SQLAlchemy()


class User(db.Model):
    """User model — covers both students and the admin."""
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(120), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    hostel        = db.Column(db.String(100), nullable=True)   # Not required for admin
    room          = db.Column(db.String(20),  nullable=True)   # Not required for admin
    role          = db.Column(db.String(10),  nullable=False, default='student')  # 'student' or 'admin'

    # Relationship: one user → many complaints
    complaints = db.relationship('Complaint', backref='student', lazy=True,
                                 cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'


class Complaint(db.Model):
    """Complaint model — submitted by students."""
    __tablename__ = 'complaints'

    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category       = db.Column(db.String(50),  nullable=False)
    description    = db.Column(db.Text,         nullable=False)
    image_filename = db.Column(db.String(256),  nullable=True)   # Optional image
    status         = db.Column(db.String(20),   nullable=False, default='Pending')
    created_at     = db.Column(db.DateTime,     nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<Complaint #{self.id} [{self.category}] {self.status}>'