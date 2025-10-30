# Import relevant modules to create the models (User, Event, Comment and Order)

from flask_login import UserMixin
from sqlalchemy import Numeric
from datetime import datetime
# Import enum type
import enum
# Import relevant modules from other parts of the code package
from . import db


# ENUMs used in the creation of the forms

# Represents what category the event is 
class EventCategory(enum.Enum):
    FOOD = "Food"
    DRINK = "Drink"
    CULTURAL = "Cultural"
    DIETARY = "Dietary"

# Represents what status the event is 
class EventStatus(enum.Enum):
    OPEN = "Open"
    INACTIVE = "Inactive"
    SOLDOUT = "Soldout"
    CANCELLED = "Cancelled"

# Represents the status of the ticket
class TicketStatus(enum.Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    CANCELLED = "Cancelled"

# User model to input into the database and instantiate user objects
class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)  # User's ID - Primary key and unique identifier
    first_name = db.Column(db.String(50), nullable=False)
    surname = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(10), unique=True, nullable=True)
    address = db.Column(db.String(50), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # Foreign key relationship to orders and comments from user
    orders = db.relationship("Order", backref="user")
    comments = db.relationship("Comment", backref="user")

# Event model to input into the database and instantiate event objects
class Event(db.Model):
    __tablename__ = "events"
    id = db.Column(db.Integer, primary_key=True) # Event's id - Primary key and unique identifier
    title = db.Column(db.String(200), nullable=False)
    image = db.Column(db.String(255), nullable=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    venue = db.Column(db.String(200), nullable=False)
    vendor_names = db.Column(db.String(255))
    description = db.Column(db.Text)
    total_tickets = db.Column(db.Integer, nullable=False)
    ticket_price = db.Column(db.Numeric(10, 2), nullable=False)
    free_sampling = db.Column(db.Boolean, default=False)
    provide_takeaway = db.Column(db.Boolean, default=False)
    category_type = db.Column(db.Enum(EventCategory), nullable=False)
    status = db.Column(db.Enum(EventStatus), default=EventStatus.OPEN)
    status_date = db.Column(db.DateTime, default=datetime.now)
    creator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Foreign key relationship between orders and comments from event
    orders = db.relationship("Order", backref="event")
    comments = db.relationship("Comment", backref="event")
    # Creator represents a foreign key between an event and a user, this ensures that users who create an event are uniquely linked by a foreign key relationship.
    creator = db.relationship("User", backref="events_created")

# Comment model to input into the database and instantiate comment objects
class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)  # Comment's id - Primary key and unique identifier
    contents = db.Column(db.Text, nullable=False)
    comment_date = db.Column(db.DateTime, default=datetime.now)

    # Foreign keys for user_id and event_id linked to a comment. Nullable is false as a comment must have a user_id and event_id linked.
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)

# Order model to be input into the database and instantiate order objects
class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)  # Order's id - Primary key and unique identifier
    tickets_purchased = db.Column(db.Integer, nullable=False)
    booking_time = db.Column(db.DateTime, default=datetime.now, nullable=False)
    purchased_amount = db.Column(Numeric(10, 2), nullable=False)
    ticket_status = db.Column(db.Enum(TicketStatus), default=TicketStatus.ACTIVE)
    purchase_ticket_price = db.Column(db.Numeric(10, 2))

    # Foreign keys links user_id and event_id to an order. Nullable is false as an order must have a user_id and event_id linked.
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)

