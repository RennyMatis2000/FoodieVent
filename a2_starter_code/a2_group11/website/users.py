from flask import Blueprint, render_template, request, session, flash, redirect
from . models import Order
from . import db
from . events import live_status
from flask_login import login_required, current_user
from . forms import check_upload_file, RegisterForm
from sqlalchemy import desc

user_bp = Blueprint('users', __name__, url_prefix='/user')

@user_bp.route('/display_booking_history')
@login_required
def display_booking_history():
    orders = db.session.scalars(db.select(Order).where(Order.user_id == current_user.id).order_by(desc(Order.booking_time))).all()
    live_status()
    return render_template('userbookinghistory.html', orders=orders)

@user_bp.route('/create_update_event')
@login_required
def create_update_event():
    return render_template('eventcreationupdate.html')