from flask import Blueprint, render_template, request, redirect, url_for, flash
from . models import Event, EventCategory
from . import db
from . events import live_status
from flask_login import login_required, current_user

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    events = db.session.scalars(db.select(Event).order_by(Event.start_time)).all()
    live_status()
    return render_template('index.html', events=events, category="")

@main_bp.route('/search')
def search():
    if request.args['search'] and request.args['search'] != "":
        print(request.args['search'])
        query = "%" + request.args['search'] + "%"
        events = db.session.scalars(
            db.select(Event).where(Event.description.like(query)).order_by(Event.start_time)).all()  
        live_status()
        if events:
            live_status()
            flash('Event has been found with a description that involves the text searched.', 'inline')
            live_status()
            return render_template('index.html', events=events)
        elif not events:  
            live_status()
            flash('No events were found with a description that involves the text searched.','inline')
            return render_template('index.html', events=events)
    else:
        live_status()
        flash('Displaying all available events. Please enter text to search.','inline')
        return redirect(url_for('main.index'))


@main_bp.route('/food')
def food():
    filteredevents = (
        db.select(Event)
          .where(Event.category_type == EventCategory.FOOD)
          .order_by(Event.start_time)
    )
    events = db.session.scalars(filteredevents).all()
    if not events:
        flash("No Food events are available right now. Please create or wait for a Food event, or browse for a different category that might entice you.", "inline")
    live_status()
    return render_template('index.html', events=events, category='Food')

@main_bp.route('/drink')
def drink():
    filteredevents = (
        db.select(Event)
          .where(Event.category_type == EventCategory.DRINK)
          .order_by(Event.start_time)
    )
    events = db.session.scalars(filteredevents).all()
    if not events:
        flash(
            "No Drink events are available right now. Please create or wait for a Drink event, or browse for a different category that might entice you.",
            "inline"
        )
    live_status()
    return render_template('index.html', events=events, category='Drink')


@main_bp.route('/cultural')
def cultural():
    filteredevents = (
        db.select(Event)
          .where(Event.category_type == EventCategory.CULTURAL)
          .order_by(Event.start_time)
    )
    events = db.session.scalars(filteredevents).all()
    if not events:
        flash(
            "No Cultural events are available right now. Please create or wait for a Cultural event, or browse for a different category that might entice you.",
            "inline"
        )
    live_status()
    return render_template('index.html', events=events, category='Cultural')


@main_bp.route('/dietary')
def dietary():
    filteredevents = (
        db.select(Event)
          .where(Event.category_type == EventCategory.DIETARY)
          .order_by(Event.start_time)
    )
    events = db.session.scalars(filteredevents).all()
    if not events:
        flash(
            "No Dietary events are available right now. Please create or wait for a Dietary event, or browse for a different category that might entice you.",
            "inline"
        )
    live_status()
    return render_template('index.html', events=events, category='Dietary')

@main_bp.route('/display_event_details')
def display_event_details():
    live_status()
    return render_template('eventdetails.html')

# @main_bp.route('/login', methods = ['GET', 'POST'])
# def login():
#     email = request.values.get("email")
#     passwd = request.values.get("pwd")
#     print (f"Email: {email}\nPassword: {passwd}")
#     # store email in session
#     session['email'] = request.values.get('email')
#     return render_template('login.html')

# @main_bp.route('/logout')
# def logout():
#     if 'email' in session:
#         session.pop('email')
#     return 'User logged out'

