from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from datetime import datetime
from . models import Event, Order, EventStatus, Comment, TicketStatus
from . forms import EventForm, CommentForm, PurchaseTicketForm, check_upload_file
from . import db
from flask_login import login_required, current_user

event_bp = Blueprint('events', __name__, url_prefix='/events')


@event_bp.route('/<event_id>')
def show(event_id):
    event = db.session.scalar(db.select(Event).where(Event.id == event_id))
    # Generate comment form
    form = CommentForm()
    # Generate purchase form
    purchase_form = PurchaseTicketForm()
    live_status()
    return render_template('events/show.html', event=event, form=form, purchase_form=purchase_form)

# Create event method


@event_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    print('Method type: ', request.method)
    # require_image=True on CREATE
    form = EventForm(require_image=True)
    form.submit.label.text = "Create Event"
    # <-- set hidden id so duplicate-title check knows this is a new event
    form.event_id.data = None

    if form.validate_on_submit():
        # image is required here, so it's safe to upload
        db_file_path = check_upload_file(form)
        event = Event(
            title=form.title.data,
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
            creator_id=current_user.id
        )
        db.session.add(event)
        db.session.commit()
        flash('Successfully created new Food and Drink Festival event', 'success')
        return redirect(url_for('main.index'))
    # Always end with redirect when form is valid
    live_status()
    return render_template('events/create.html', form=form)

# Update event method


@event_bp.route('/<int:event_id>/update', methods=['GET', 'POST'])
@login_required
def update(event_id):
    print('Method type: ', request.method)
    event = db.session.get(Event, event_id)
    # require_image=False on UPDATE (optional)
    form = EventForm(obj=event, require_image=False)
    form.submit.label.text = "Update Event"
    form.event_id.data = event.id  # <-- set hidden id so validators can exclude this row

    if form.validate_on_submit():
        # Only replace image if a new file was chosen
        new_file = form.image.data
        if new_file and getattr(new_file, "filename", ""):
            db_file_path = check_upload_file(form)
            event.image = db_file_path  # replace
        # else: keep existing event.image

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

        message = ("Successfully updated Food and Drink Festival event.")
        prev_status = event.status

        # --- Status actions ---
        if form.cancel_event.data:
            # Only restock + cancel orders the first time we move to CANCELLED
            if prev_status != EventStatus.CANCELLED:
                # Get ACTIVE orders holding inventory
                active_orders = (
                    [orders for orders in getattr(
                        event, "orders", []) if orders.ticket_status == TicketStatus.ACTIVE]
                    if hasattr(event, "orders")
                    else db.session.scalars(
                        db.select(Order).where(
                            Order.event_id == event.id,
                            Order.ticket_status == TicketStatus.ACTIVE
                        )
                    ).all()
                )

                tickets_to_return = sum((orders.tickets_purchased or 0)
                                        for orders in active_orders)
                total_refund = sum((orders.purchased_amount or 0)
                                   for orders in active_orders)

                # Return tickets to availability
                event.total_tickets = (
                    event.total_tickets or 0) + (tickets_to_return or 0)

                # Cancel those orders so they stop holding inventory
                for orders in active_orders:
                    orders.ticket_status = TicketStatus.CANCELLED

                message = (
                    f"Successfully updated event. Event has been cancelled. {tickets_to_return} tickets have been refunded and resupplied. Total amount refunded: ${total_refund}")
            else:
                message = "Event was already cancelled. Details updated."

            event.status = EventStatus.CANCELLED

        elif form.reopen_event.data:
            if prev_status == EventStatus.CANCELLED:
                event.status = EventStatus.OPEN
                message = "Successfully updated event. Event has been re-opened."

        db.session.commit()
        flash(f'{message}', 'success')
        live_status()
        return redirect(url_for('events.show', event_id=event.id))
        # Always end with redirect when form is valid
    live_status()
    return render_template('events/update.html',  form=form, event=event)

# Cancel event


@event_bp.route('/<int:event_id>/cancel', methods=['GET', 'POST'])
@login_required
def cancel(event_id):
    # Fetch the event by ID
    event = db.session.get(Event, event_id)
    if event.creator_id != current_user.id:
        flash(
            f'The event: {event.title} was not created by the currently logged in user.', 'danger')
        return redirect(url_for('events.update', event_id=event.id))

    if event.status != EventStatus.CANCELLED:
        event.status = EventStatus.CANCELLED
        db.session.commit()
        flash(f'The event: {event.title} has been cancelled.', 'success')
    elif event.status == EventStatus.CANCELLED:
        event.status = EventStatus.OPEN
        db.session.commit()
        flash(f'The event: {event.title} has been re-opened. If this is an outdated event, the status will be inactive. If this event has 0 tickets, the status will be soldout.', 'success')
    else:
        flash(
            f'The event: {event.title} cannot be cancelled, as it is already cancelled.', 'success')

    return redirect(url_for('events.update', event_id=event.id))

# Cancel order


@event_bp.route('/<int:order_id>/cancel_order', methods=['GET', 'POST'])
@login_required
def cancel_order(order_id):
    # Fetch the order by ID
    order = db.session.get(Order, order_id)
    if order.ticket_status != TicketStatus.CANCELLED:
        order.ticket_status = TicketStatus.CANCELLED
        order.event.total_tickets = (
            order.event.total_tickets + order.tickets_purchased)
        db.session.commit()
        flash(f'The order #{order.id} has been cancelled.', 'success')

    return redirect(url_for('users.display_booking_history'))

# Purchase tickets to generate an order, and redirect to booking history page


@event_bp.route('/<int:event_id>/purchase', methods=['GET', 'POST'])
@login_required
def purchase_tickets(event_id):
    event = db.session.get(Event, event_id)
    form = PurchaseTicketForm()

    if form.validate_on_submit():
        tickets = form.tickets_purchased.data

        if tickets > event.total_tickets:
            flash(
                f'Order was unable to be booked, please enter a value less than the remaining amount of tickets. Tickets remaining: {event.total_tickets}.', 'danger')
            return redirect(url_for('events.show', event_id=event.id))
        elif tickets <= event.total_tickets:
            order = Order(
                event_id=event.id,
                user_id=current_user.id,
                tickets_purchased=form.tickets_purchased.data,
                purchase_ticket_price=event.ticket_price,
                purchased_amount=event.ticket_price * form.tickets_purchased.data,
                ticket_status=TicketStatus.ACTIVE,
                booking_time=datetime.now()
            )
            event.total_tickets -= tickets
            if event.total_tickets == 0:
                event.status = EventStatus.SOLDOUT

            db.session.add(order)
            db.session.commit()
            flash(
                f'Thank you for your purchase! Your order number is #{order.id}. {order.tickets_purchased} tickets have been purchased for ${order.purchased_amount}.', 'success')
            return redirect(url_for('users.display_booking_history'))
            # Always end with redirect when form is valid
    live_status()
    return redirect(url_for('events.show', event_id=event.id))


@event_bp.route('/<int:event_id>/comment', methods=['GET', 'POST'])
@login_required
def comment(event_id):
    # here the form is created form = CommentForm()
    form = CommentForm()
    event = db.session.scalar(db.select(Event).where(Event.id == event_id))
    if form.validate_on_submit():
        # read the current form
        comment = Comment(
            contents=form.contents.data,
            user_id=current_user.id,
            event=event)
        db.session.add(comment)
        db.session.commit()
        flash("Your comment has been posted.", "comment")

    # using redirect sends a GET request to destination.show
    live_status()
    return redirect(url_for('events.show', event_id=event_id) + "#comments")


def live_status():
    now = datetime.now()
    events = db.session.scalars(db.select(Event)).all()
    orders = db.session.scalars(db.select(Order)).all()

    for event in events:
        if event.status == EventStatus.CANCELLED:
            # Event stays cancelled until end time is in the past, then turns to inactive
            if event.end_time and now > event.end_time:
                new_status = EventStatus.INACTIVE
            else:
                new_status = EventStatus.CANCELLED
        elif (event.total_tickets or 0) <= 0:
            new_status = EventStatus.SOLDOUT
        elif event.end_time and now <= event.end_time:
            new_status = EventStatus.OPEN
        else:
            new_status = EventStatus.INACTIVE

        if event.status != new_status:
            event.status = new_status
            event.status_date = now

    for order in orders:
        event_order = order.event

        if event_order.status == EventStatus.CANCELLED:
            new_ticketstatus = TicketStatus.CANCELLED
        elif event_order.status == EventStatus.INACTIVE:
            new_ticketstatus = TicketStatus.INACTIVE
        else:
            if order.ticket_status == TicketStatus.CANCELLED:
                if event_order.end_time and now > event_order.end_time:
                    new_ticketstatus = TicketStatus.INACTIVE
                else:
                    new_ticketstatus = TicketStatus.CANCELLED
            elif event_order.end_time and now <= event_order.end_time:
                new_ticketstatus = TicketStatus.ACTIVE
            else:
                new_ticketstatus = TicketStatus.INACTIVE

        if order.ticket_status != new_ticketstatus:
            order.ticket_status = new_ticketstatus

    db.session.commit()
