# From flask import relevasnt modules
from flask import Blueprint, render_template, request, redirect, url_for, flash
# Import relevant modules from other files in the code package
from . models import Event, EventCategory
from . import db
from . events import live_status

# Main blueprint displays all main pages
main_bp = Blueprint('main', __name__)

# Main blue print route to the landing page (home page) by using a forward slash
@main_bp.route('/')
# Returns index.html which is the landing page (home page) method
def index():
    # Retrieve all events and sort them by start time so they are most recent
    events = db.session.scalars(db.select(Event).order_by(Event.start_time)).all()
    # Update all events and tickets to be a live version of the status and redirect to main page
    live_status()
    return render_template('index.html', events=events, category="")

# Main blue print that allows searching based on text
@main_bp.route('/search')
# Text based search method
def search():
    # Search events based on the search argument presented by the user
    if request.args['search'] and request.args['search'] != "":
        print(request.args['search'])
        query = "%" + request.args['search'] + "%"
        # Retrieve events based on this search argument, and filter them by start time for most recent
        events = db.session.scalars(
            db.select(Event).where(Event.description.like(query)).order_by(Event.start_time)).all()  
        if events:
            # If events have been found based on the text search input, flash a successful message and update and return to main page with those events
            flash('Event has been found with a description that involves the text searched.', 'inline')
            live_status()
            return render_template('index.html', events=events)
        elif not events:  
            # If events have NOT been found based on the text search input, flash an unsuccessful message and update and return to main page with those events
            live_status()
            flash('No events were found with a description that involves the text searched.','inline')
            return render_template('index.html', events=events)
    else:
        # If user decided to input nothing and click search, update events and ticket status to live and flash a warning message
        live_status()
        flash('Displaying all available events. Please enter text to search.','inline')
        return redirect(url_for('main.index'))

# Main blue print that allows user to only see events based on the FOOD event category
@main_bp.route('/food')
# Method to filter to FOOD event category
def food():
    # Retrieve all events where the event category is FOOD
    filteredevents = (
        db.select(Event)
          .where(Event.category_type == EventCategory.FOOD)
          .order_by(Event.start_time)
    )
    # Retrieve all events that are filtered to the accurate event category
    events = db.session.scalars(filteredevents).all()
    # If no events were found with the FOOD category
    if not events:
        # Flash error message if no events were found with the FOOD category
        flash("No Food events are available right now. Please create or wait for a Food event, or browse for a different category that might entice you.", "inline")
    # Update event and ticket status to live and return to the main page with FOOD events displayed
    live_status()
    return render_template('index.html', events=events, category='Food')

# Main blue print that allows user to only see events based on the DRINK event category
@main_bp.route('/drink')
# Method to filter to DRINK event category
def drink():
    # Retrieve all events where the event category is DRINK
    filteredevents = (
        db.select(Event)
          .where(Event.category_type == EventCategory.DRINK)
          .order_by(Event.start_time)
    )
    # Retrieve all events that are filtered to the accurate event category
    events = db.session.scalars(filteredevents).all()
    # If no events were found with the DRINK category
    if not events:
        # Flash error message if no events were found with the DRINK category
        flash(
            "No Drink events are available right now. Please create or wait for a Drink event, or browse for a different category that might entice you.",
            "inline"
        )
    # Update event and ticket status to live and return to the main page with DRINK events displayed
    live_status()
    return render_template('index.html', events=events, category='Drink')

# Main blue print that allows user to only see events based on the CULTURAL event category
@main_bp.route('/cultural')
# Method to filter to CULTURAL event category
def cultural():
    filteredevents = (
        db.select(Event)
          .where(Event.category_type == EventCategory.CULTURAL)
          .order_by(Event.start_time)
    )
    # Retrieve all events that are filtered to the accurate event category
    events = db.session.scalars(filteredevents).all()
    # Flash error message if no events were found with the CULTURAL category
    if not events:
        flash(
            "No Cultural events are available right now. Please create or wait for a Cultural event, or browse for a different category that might entice you.",
            "inline"
        )
    # Update event and ticket status to live and return to the main page with CULTURAL events displayed
    live_status()
    return render_template('index.html', events=events, category='Cultural')

# Main blue print that allows user to only see events based on the DIETARY event category
@main_bp.route('/dietary')
# Method to filter to DIETARY event category
def dietary():
    filteredevents = (
        db.select(Event)
          .where(Event.category_type == EventCategory.DIETARY)
          .order_by(Event.start_time)
    )
    # Retrieve all events that are filtered to the accurate event category
    events = db.session.scalars(filteredevents).all()
    # Flash error message if no events were found with the DIETARY category
    if not events:
        flash(
            "No Dietary events are available right now. Please create or wait for a Dietary event, or browse for a different category that might entice you.",
            "inline"
        )
    # Update event and ticket status to live and return to the main page with DIETARY events displayed
    live_status()
    return render_template('index.html', events=events, category='Dietary')
