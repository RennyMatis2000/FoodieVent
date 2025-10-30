# Import flask and modules required
from flask import Blueprint, redirect, url_for, flash
from flask_login import login_required, current_user
# Import datetime
from datetime import datetime
# Import relevant modules from other python files in the package
from . events import live_status
from . models import Event, Order, EventStatus, TicketStatus
from . forms import PurchaseTicketForm
from . import db

# Order blueprint route to handle order associated methods
order_bp = Blueprint('orders', __name__, url_prefix='/order')

# Order blueprint route for cancelling an order using order_id and get and post
@order_bp.route('/<int:order_id>/cancel_order', methods=['GET', 'POST'])
# User must be logged in to cancel an order, as orders are attached to users
@login_required
# Cancel order method
def cancel_order(order_id):
    # Retrieve the order based on the order_id
    order = db.session.get(Order, order_id)
    # If ticket status is not cancelled, user can set the ticket status to cancelled
    if order.ticket_status != TicketStatus.CANCELLED:
        order.ticket_status = TicketStatus.CANCELLED
        # Update the total tickets of the event by adding the purchased tickets amount back (e.g. a user purchased 50 tickets, if they cancel their order the event owner can sell 50 more tickets)
        order.event.total_tickets = (order.event.total_tickets + order.tickets_purchased)
        # commit and flash order number has been cancelled.
        db.session.commit()
        flash(f'The order #{order.id} for the event {order.event.title} has been cancelled.', 'success')
    # Redirect to the users booking history page on cancellation
    return redirect(url_for('users.display_booking_history'))

# Order blueprint route for event_id to purchase an order using get and post
@order_bp.route('/<int:event_id>/purchase', methods=['GET', 'POST'])
# User must be logged in to purchase, otherwise redirected to login page
@login_required
# Purchase tickets method using event_id to show which event the ticket purchase is on
def purchase_tickets(event_id):
    # Retrieve event from the database based on event id
    event = db.session.get(Event, event_id)
    # Form to be used is the purchase ticket form
    form = PurchaseTicketForm()

    # If the form is submitted validly, user is able to generate an order
    if form.validate_on_submit():
        # Tickets is the amount purchased
        tickets = form.tickets_purchased.data
        # If condition checks multiple tabs error (e.g. a user purchases tickets, and in that time another user also tries to purchase over the available amount)
        if tickets > event.total_tickets:
            # Flash and redirect if users purchase shortly after one another
            flash(f'Order was unable to be booked, please enter a value less than the remaining amount of tickets. Tickets remaining: {event.total_tickets}.', 'danger')
            return redirect(url_for('events.show', event_id=event.id))
        # Otherwise, if ticket purchase amount is equal or less than total ticket amount and not restrained by the purchase ticket form integer calidation
        elif tickets <= event.total_tickets:
            # Order can be generated using form data
            order = Order(
                # Current event and user
                event_id=event.id,
                user_id=current_user.id,
                tickets_purchased=form.tickets_purchased.data,
                # Retrieve ticket_price from the event
                purchase_ticket_price=event.ticket_price,
                # Calculate total amount based on events ticket_price and tickets_purchased amount
                purchased_amount=event.ticket_price * form.tickets_purchased.data,
                # Default ticket status
                ticket_status=TicketStatus.ACTIVE,
                # Stamp booking time
                booking_time=datetime.now()
            )
            # Add total_tickets based on tickets
            event.total_tickets -= tickets
            # If tickets reach 0, set event status to soldout
            if event.total_tickets == 0:
                event.status = EventStatus.SOLDOUT

            # Commit order and add to database
            db.session.add(order)
            db.session.commit()
            # Flash order number, tickets purchased, and purchased amount for the user and update event and ticket status to live then redirect to display booking hisory page.
            flash(f'Thank you for your purchase! Your order number is #{order.id}. {order.tickets_purchased} tickets have been purchased for ${order.purchased_amount}.', 'success')
            live_status()
            return redirect(url_for('users.display_booking_history'))
            # Always end with redirect when form is valid
    # Update event and ticket status if unsuccessful and return to the event details page for that id.
    live_status()
    return redirect(url_for('events.show', event_id=event.id))