from flask_wtf            import FlaskForm
from flask_wtf.file       import FileField, FileAllowed
from wtforms              import (StringField, PasswordField, SelectField,
                                  TextAreaField, SubmitField)
from wtforms.validators   import DataRequired, Email, EqualTo, Length, Optional

# ── Allowed image extensions (also enforced server-side in app.py) ────────────
IMAGE_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif', 'webp']

# Complaint category choices
CATEGORY_CHOICES = [
    ('', '-- Select Category --'),
    ('Electricity', 'Electricity'),
    ('Water',       'Water'),
    ('Wi-Fi',       'Wi-Fi'),
    ('Cleaning',    'Cleaning'),
    ('Mess',        'Mess'),
    ('Room',        'Room'),
    ('Furniture',   'Furniture'),
    ('Other',       'Other'),
]

STATUS_CHOICES = [
    ('Pending',     'Pending'),
    ('In Progress', 'In Progress'),
    ('Resolved',    'Resolved'),
]


class RegistrationForm(FlaskForm):
    """Student registration form."""
    name     = StringField('Full Name',    validators=[DataRequired(), Length(min=2, max=120)])
    email    = StringField('Email',        validators=[DataRequired(), Email()])
    password = PasswordField('Password',   validators=[DataRequired(), Length(min=6)])
    confirm  = PasswordField('Confirm Password',
                             validators=[DataRequired(), EqualTo('password',
                             message='Passwords must match.')])
    hostel   = StringField('Hostel Name',  validators=[DataRequired(), Length(max=100)])
    room     = StringField('Room Number',  validators=[DataRequired(), Length(max=20)])
    submit   = SubmitField('Register')


class LoginForm(FlaskForm):
    """Student login form."""
    email    = StringField('Email',    validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit   = SubmitField('Login')


class AdminLoginForm(FlaskForm):
    """Admin login form (separate route/template)."""
    email    = StringField('Admin Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password',  validators=[DataRequired()])
    submit   = SubmitField('Admin Login')


class ComplaintForm(FlaskForm):
    """Complaint submission form."""
    category    = SelectField('Category',    choices=CATEGORY_CHOICES,
                              validators=[DataRequired(message='Please select a category.')])
    description = TextAreaField('Description',
                                validators=[DataRequired(), Length(min=10, max=2000)])
    image       = FileField('Attach Image (optional)',
                            validators=[Optional(),
                                        FileAllowed(IMAGE_EXTENSIONS,
                                                    'Images only (png, jpg, jpeg, gif, webp)!')])
    submit      = SubmitField('Submit Complaint')


class UpdateStatusForm(FlaskForm):
    """Admin: update complaint status."""
    status = SelectField('Status', choices=STATUS_CHOICES, validators=[DataRequired()])
    submit = SubmitField('Update')