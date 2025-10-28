from flask import Blueprint, flash, render_template, request, url_for, redirect
from flask_bcrypt import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user
from .models import User
from .forms import LoginForm, RegisterForm
from . import db
from . events import live_status

# Create a blueprint - make sure all BPs have unique names
auth_bp = Blueprint('auth', __name__)

# this is a hint for a login function
@auth_bp.route('/login', methods=['GET', 'POST'])
# view function
def login():
    login_form = LoginForm()
    if login_form.validate_on_submit():
        email = login_form.email.data
        password = login_form.password.data

        # make sure error exists regardless of the path taken
        error = None

        user = db.session.scalar(db.select(User).where(User.email == email))
        if user is None:
            error = 'Incorrect email'
        elif not check_password_hash(user.password_hash, password):
            error = 'Incorrect password'

        if error:
            flash(error, 'danger')
        else:
            login_user(user)
            nextp = request.args.get('next')
            if not nextp or not nextp.startswith('/'):
                live_status()
                flash(f"{user.first_name} {user.surname} has logged-in successfully. Welcome to FoodieVent!", 'success')
                return redirect(url_for('main.index'))
            return redirect(nextp)

    return render_template('user.html', form=login_form, heading='Login')

@auth_bp.route('/register', methods=['GET','POST'])
def register():
    form = RegisterForm()
    error = None
    if form.validate_on_submit():
        user = User(
            first_name=form.first_name.data,
            surname=form.surname.data,
            email=form.email.data,
            phone=form.phone.data,
            address=form.address.data,   
            password_hash=generate_password_hash(form.password.data)
        )
        db.session.add(user)
        db.session.commit()
        flash(f"{user.first_name} {user.surname} has successfully registered an account for FoodieVent.", 'success')
        return redirect(url_for('auth.login'))
    return render_template('user.html', form=form, heading = 'Register an Account')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    live_status()
    user = db.session.scalar(db.select(User))
    flash(f"{user.first_name} {user.surname} has logged out.", 'success')
    return redirect(url_for('main.index'))