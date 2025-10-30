# Import flask and associated modules
from flask import Blueprint, flash, render_template, request, url_for, redirect
from flask_bcrypt import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user, current_user
# Import modules from other code inside the package
from .models import User
from .forms import LoginForm, RegisterForm
from . import db
from . events import live_status

# Create a blueprint - make sure all BPs have unique names
auth_bp = Blueprint('auth', __name__)

# Authentication blueprint route method with get and post
@auth_bp.route('/login', methods=['GET', 'POST'])
# Login method
def login():
    # Use the login form
    login_form = LoginForm()
    if login_form.validate_on_submit():
        # Email and password are retrieved from the login form
        email = login_form.email.data
        password = login_form.password.data

        # Make sure error exists regardless of path taken
        error = None

        # Retrieve user that has the same email address (email address is a unique identifier of the user)
        user = db.session.scalar(db.select(User).where(User.email == email))
        # If no user found
        if user is None:
            error = 'Incorrect email'
        # If a user is found with the correct hashed password
        elif not check_password_hash(user.password_hash, password):
            error = 'Incorrect password'
        # Flash if error is found
        if error:
            flash(error, 'danger')
        else:
            # Valid login attempt
            login_user(user)
            nextp = request.args.get('next')
            if not nextp or not nextp.startswith('/'):
                # Update all event and ticket statuses to live
                live_status()
                # User has successfully logged in and is directed to the main page
                flash(f"{user.first_name} {user.surname} has logged-in successfully. Welcome to FoodieVent!", 'success')
                return redirect(url_for('main.index'))
            return redirect(nextp)

    # Return to login page if user is unable to login
    return render_template('user.html', form=login_form, heading='Login')

# Authentication blue print route for registering with get and post 
@auth_bp.route('/register', methods=['GET','POST'])
# Register method
def register():
    # Use register form to register
    form = RegisterForm()
    # If form is submitted with all correct fields
    if form.validate_on_submit():
        # Instantiate a user with form data
        user = User(
            first_name=form.first_name.data,
            surname=form.surname.data,
            email=form.email.data,
            phone=form.phone.data,
            address=form.address.data,   
            # Hash the password
            password_hash=generate_password_hash(form.password.data)
        )
        # Add new user to the database and commit
        db.session.add(user)
        db.session.commit()
        # Flash user successfully registered message and redirect to login page
        flash(f"{user.first_name} {user.surname} has successfully registered an account for FoodieVent.", 'success')
        return redirect(url_for('auth.login'))
    # Always return to register page if user did not successfully submit the form
    return render_template('user.html', form=form, heading = 'Register an Account')

# Authentication blue print route for logging out
@auth_bp.route('/logout')
# User must be logged in
@login_required
# Logout method
def logout():
    # Flash logout message and log user out, update event status and return main page
    name = f"{current_user.first_name} {current_user.surname}"
    logout_user()
    live_status()
    flash(f"{name} has logged out.", 'success')
    return redirect(url_for('main.index'))