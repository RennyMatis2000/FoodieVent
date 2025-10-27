from . import db
from datetime import datetime
import enum
from flask_login import UserMixin
from sqlalchemy import Numeric 

class EventCategory(enum.Enum):
    FOOD = "Food"
    DRINK = "Drink"
    CULTURAL = "Cultural"
    DIETARY = "Dietary"

class EventStatus(enum.Enum):
    OPEN = "Open"
    INACTIVE = "Inactive"
    SOLDOUT = "Soldout"
    CANCELLED = "Cancelled"

class TicketStatus(enum.Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    CANCELLED = "Cancelled"

class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)  # user's id
    first_name = db.Column(db.String(50), nullable=False)
    surname = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(10), unique=True, nullable=True)
    address = db.Column(db.String(50), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)

    orders = db.relationship("Order", backref="user")
    comments = db.relationship("Comment", backref="user")

class Event(db.Model):
    __tablename__ = "events"
    id = db.Column(db.Integer, primary_key=True) # event's id
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

    orders = db.relationship("Order", backref="event")
    comments = db.relationship("Comment", backref="event")
    creator = db.relationship("User", backref="events_created")

    def __repr__(self):
        return f"Name: {self.title}"

class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)  # comment's id
    contents = db.Column(db.Text, nullable=False)
    comment_date = db.Column(db.DateTime, default=datetime.now)

    # Foreign keys -> now point to users.id / events.id
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)

    def __repr__(self):
        return f"Name: {self.id}"

class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)  # order's id
    tickets_purchased = db.Column(db.Integer, nullable=False)
    booking_time = db.Column(db.DateTime, default=datetime.now, nullable=False)
    purchased_amount = db.Column(Numeric(10, 2), nullable=False)
    ticket_status = db.Column(db.Enum(TicketStatus), default=TicketStatus.ACTIVE)

    # Foreign keys -> now point to users.id / events.id
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)

    def __repr__(self):
        return f"Name: {self.id}"
