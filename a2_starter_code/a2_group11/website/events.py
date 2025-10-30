# Import flask and modules required
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
# Import datetime
from datetime import datetime
# Import relevant modules from other python files in the package
from . models import Event, Order, EventStatus, Comment, TicketStatus
from . forms import EventForm, CommentForm, PurchaseTicketForm, check_upload_file
from . import db

# Event blueprint
event_bp = Blueprint('events', __name__, url_prefix='/events')

# Event blue print route based on event_id
@event_bp.route('/<event_id>')
# Show method that displays an event based on the event_id
def show(event_id):
    # Get an event to display the page where event_id is the same as event.id in the database
    event = db.session.scalar(db.select(Event).where(Event.id == event_id))
    # Generate comment form
    form = CommentForm()
    # Generate purchase form
    purchase_form = PurchaseTicketForm()
    # Update events to live status before returning the template
    live_status()
    return render_template('events/show.html', event=event, form=form, purchase_form=purchase_form)

# Event blueprint route to create an event with get and post 
@event_bp.route('/create', methods=['GET', 'POST'])
# Creating an event requires the user to be logged in
@login_required
# Create an event method
def create():
    # Print the method for get and post for logging
    print('Method type: ', request.method)
    # require_image=True on CREATE
    form = EventForm(require_image=True)
    # Ensure the submit button is labelled as Create Event, as it is shared with the update button
    form.submit.label.text = "Create Event"

    # If the event form has been submitted validly, generate an event
    if form.validate_on_submit():
        # Image is required here, so it's safe to upload
        db_file_path = check_upload_file(form)
        # Instantiate an event using the form data
        event = Event(
            title=form.title.data,
            # Image is retrieved from db_file_path
            image=db_file_path,
            start_time=form.start_time.data,
            end_time=form.end_time.data,
            venue=form.venue.data,
            vendor_names=form.vendor_names.data,
            description=form.description.data,
            total_tickets=form.total_tickets.data,
            ticket_price=form.ticket_price.data,
            free_sampling=form.free_sampling.data,
            provide_takeaway=form.provide_takeaway.data,
            category_type=form.category_type.data,
            # Creator of the event is the current logged in user
            creator_id=current_user.id
        )
        # Add and commit the newly created event to the database
        db.session.add(event)
        db.session.commit()
        # Flash event has been successfully created and return to main page
        flash(f'Successfully created new Food and Drink Festival event titled: {event.title}', 'success')
        live_status()
        return redirect(url_for('main.index'))
    # Redirect to event create page if form is not valid
    live_status()
    return render_template('events/create.html', form=form)

# Event blueprint route to update with an event id, using get and post
@event_bp.route('/<int:event_id>/update', methods=['GET', 'POST'])
# User must be logged in
@login_required
# Update an event method using the event id
def update(event_id):
    # Print the method for get and post for logging
    print('Method type: ', request.method)
    # Get event based on event id in the database
    event = db.session.get(Event, event_id)
    # require_image=False on UPDATE, user does not need to reinput the image to update
    form = EventForm(obj=event, require_image=False)
    # Ensure submit button is labelled as Update Event, as it is shared with the create button
    form.submit.label.text = "Update Event"

    form.event_id.data = event.id  

    # If the form is submitted validly
    if form.validate_on_submit():
        # Only replace image if a new image was submitted
        new_file = form.image.data
        if new_file and getattr(new_file, "filename", ""):
            db_file_path = check_upload_file(form)
            event.image = db_file_path  # replace
        # Otherwise keep the existing event.image

        # Update form fields that will be updated with what is input into the form, directly changes the specific events fields
        event.title = form.title.data
        event.start_time = form.start_time.data
        event.end_time = form.end_time.data
        event.venue = form.venue.data
        event.vendor_names = form.vendor_names.data
        event.description = form.description.data
        event.total_tickets = form.total_tickets.data
        event.ticket_price = form.ticket_price.data
        event.free_sampling = form.free_sampling.data
        event.provide_takeaway = form.provide_takeaway.data
        event.category_type = form.category_type.data

        # Display a message showing user has successfully updated the specific even 
        message = (f"Successfully updated Food and Drink Festival event titled: {event.title}.")

        # Previous event status equals current event status
        prev_status = event.status

        # If condition for cancelling an event, if also is used to restock all tickets that have been sold
        if form.cancel_event.data:
            # Restock and cancel orders if the previous status does not equal cancel yet
            if prev_status != EventStatus.CANCELLED:
                # Retrieve active orders on this event, where the Ticket status is active
                active_orders = (
                    [orders for orders in getattr(event, "orders", []) if orders.ticket_status == TicketStatus.ACTIVE]
                    # If event has attribute orders (event may have no orders yet)
                    if hasattr(event, "orders")
                    # Otherwise select all orders from the event_id of the update page that has the event.id in the database, and has a ticket status of active
                    else db.session.scalars(db.select(Order).where(Order.event_id == event.id,Order.ticket_status == TicketStatus.ACTIVE)).all()
                )

                # Total amount of tickets that need to be returned that were purchased for active orders
                tickets_to_return = sum((orders.tickets_purchased or 0) for orders in active_orders)
                # Total amount of money to be refunded based on the purchased amount for active orders
                total_refund = sum((orders.purchased_amount or 0) for orders in active_orders)

                # Update the events total_tickets variable based on amount of tickets to return
                event.total_tickets = (event.total_tickets or 0) + (tickets_to_return or 0)

                # Cancel the orders ticket status as the event status has been cancelled
                for orders in active_orders: orders.ticket_status = TicketStatus.CANCELLED
                
                # Display a message of how many tickets have been returned and amount of money refunded
                message = (f"Successfully updated event titled: {event.title}. {event.title} has been cancelled. {tickets_to_return} tickets have been refunded and resupplied. Total amount refunded: ${total_refund}")

        # Elif condition if the user wants to re-open the event from cancelled
        elif form.reopen_event.data:
            # Change event status to open and 
            if prev_status == EventStatus.CANCELLED:
                event.status = EventStatus.OPEN
                # Success message
                message = f"Successfully updated event titled: {event.title}. {event.title} has been re-opened."

        # Commit the changes and flash the message
        db.session.commit()
        flash(f'{message}', 'success')
        # Update event and ticket status to live and redirect to the events.show for the specific event updated
        live_status()
        return redirect(url_for('events.show', event_id=event.id))
    # Update events and ticket status to live, but show the update page if event has not been updated properly
    live_status()
    return render_template('events/update.html',  form=form, event=event)

# Event blueprint route for commenting based on event id using get and post
@event_bp.route('/<int:event_id>/comment', methods=['GET', 'POST'])
# User must be logged in to comment, otherwise redirect to login page and flash warning
@login_required
# Comment method based on event ID
def comment(event_id):
    # Comment form
    form = CommentForm()
    # Retrieve event where event.id is event_id of the page
    event = db.session.scalar(db.select(Event).where(Event.id == event_id))
    # If form is submitted validly
    if form.validate_on_submit():
        # Create the comment based on the comment form
        comment = Comment(
            # Contents is what the user types, then the user and current event
            contents=form.contents.data,
            user_id=current_user.id,
            event=event)
        # Commit and add to database, flash comment
        db.session.add(comment)
        db.session.commit()
        flash(f"Your comment has been posted. It is comment #{comment.id} on FoodieVent.", "comment")
        # Update event and ticket status and redirect to events detail page for that event id.
        live_status()
        return redirect(url_for('events.show', event_id=event_id) + "#comments")
    
    # Update event and ticket status and return flash message stating comment could not be posted.
    live_status()
    flash(f"Your comment was unable to be posted, please ensure you enter a valid comment.", "comment")
    return redirect(url_for('events.show', event_id=event_id) + "#comments")


# Live status method, that keeps the status updated live dependent on conditions
def live_status():
    # Now is the current time using datetime
    now = datetime.now()
    # Select all events and orders from the database for updating
    events = db.session.scalars(db.select(Event)).all()
    orders = db.session.scalars(db.select(Order)).all()

    # Ensure all events are selected and looped over
    for event in events:
        # If event is cancelled
        if event.status == EventStatus.CANCELLED:
            # Event stays cancelled until end time is in the past, then turns to inactive
            if now > event.end_time:
                new_status = EventStatus.INACTIVE
            else:
                new_status = EventStatus.CANCELLED
        # If total_tickets of an event or 0 are equal to or less than 0, set status to soldout
        elif (event.total_tickets or 0) <= 0:
            new_status = EventStatus.SOLDOUT
        # If end_time is greater than the current time event is open
        elif now <= event.end_time:
            new_status = EventStatus.OPEN
        # Otherwise if now is greater than end_time, event has ended already.
        else:
            new_status = EventStatus.INACTIVE

        # If event status is not the new status set it to the new status
        if event.status != new_status:
            event.status = new_status
            # Set event status variable stamped to now
            event.status_date = now

    # Ensure all orders are selected and looped over
    for order in orders:
        # Event order is the order attached to the event variable 
        event_order = order.event

        # If the event attached to the order is cancelled
        if event_order.status == EventStatus.CANCELLED:
            # Also set the ticket status to cancelled
            new_ticketstatus = TicketStatus.CANCELLED
        # If event attached to the order is inactive
        elif event_order.status == EventStatus.INACTIVE:
            # Also set the ticket status to inactive
            new_ticketstatus = TicketStatus.INACTIVE
        # Otherwise handle if ticket status has been cancelled
        else:
            # If ticket status is cancelled
            if order.ticket_status == TicketStatus.CANCELLED:
                # If now is greater than the event.end_time attached to the order, set ticket status to inactive even if cancelled
                if now > event_order.end_time:
                    new_ticketstatus = TicketStatus.INACTIVE
                # Otherwise ticket status is just cancelled if event is still active 
                else:
                    new_ticketstatus = TicketStatus.CANCELLED
            # If end time of the event is in the future
            elif now <= event_order.end_time:
                # Set ticket status to active
                new_ticketstatus = TicketStatus.ACTIVE
            else:
                # Otherwise set it to inactive
                new_ticketstatus = TicketStatus.INACTIVE
        # If ticket status is not the new ticket status, set it to the new one
        if order.ticket_status != new_ticketstatus:
            order.ticket_status = new_ticketstatus

    # Commit live changes to the database
    db.session.commit()