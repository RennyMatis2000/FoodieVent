# Import flask, sqlalchemy and relevant modules
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import desc
# Import relevant modules from other parts of the code package
from . models import Order
from . import db
from . events import live_status

# User blueprint
user_bp = Blueprint('users', __name__, url_prefix='/user')

# User blue print route to display booking history of a user
@user_bp.route('/display_booking_history')
# Login is required, as a user should not be able to access a booking history if they are not logged in
@login_required
# Method to display booking history
def display_booking_history():
    # Locate all orders in the database if they have the same user id as the current logged in user, then sort by newest bookings based on booking time stamp
    orders = db.session.scalars(db.select(Order).where(Order.user_id == current_user.id).order_by(desc(Order.booking_time))).all()
    live_status()
    return render_template('userbookinghistory.html', orders=orders)