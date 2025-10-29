# forms.py

from datetime import datetime, timedelta
import os
import re

from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired, FileField, FileAllowed
from sqlalchemy import func
from werkzeug.utils import secure_filename
from wtforms.fields import (
    TextAreaField, SubmitField, StringField, TelField, IntegerField, SelectField,
    BooleanField, PasswordField, DateTimeLocalField, DecimalField, HiddenField
)
from wtforms.validators import DataRequired, InputRequired, Length, Email, EqualTo, NumberRange, ValidationError

from .models import EventCategory, User, Event
from . import db

# ---------- Constants ----------
ALLOWED_FILE = {'PNG', 'JPG', 'JPEG', 'png', 'jpg', 'jpeg'}

# common domain endings for simple email-typo guard
COMMON_TLDS = {
    "com", "net", "org", "edu", "gov", "io", "me", "ai", "dev",
    "co", "uk", "au", "nz", "ca", "us", "de", "fr", "sg", "jp",
    "com.au", "net.au", "org.au", "edu.au", "gov.au",
}

# ---------- Filters ----------


def _strip(s: str) -> str | None:
    """Trim leading/trailing whitespace; keep internal spaces."""
    return s.strip() if s else s


def _collapse_spaces(s: str) -> str | None:
    """Trim then collapse multiple internal spaces to a single space."""
    return re.sub(r"\s+", " ", s.strip()) if s else s


def _lower(s: str) -> str | None:
    """Lowercase and trim."""
    return s.lower().strip() if s else s


def _digits_only(s: str) -> str:
    """Remove all non-digits (useful for phones)."""
    return re.sub(r"\D", "", s or "")

# ---------- Helpers ----------


def _tld_or_sld_ok(addr: str) -> bool:
    """
    Allow only common domain endings to catch obvious typos like '.coddddd'.
    Handles both single TLDs (example.com) and 2-part SLDs (example.com.au).
    """
    if "@" not in addr:
        return False
    dom = addr.split("@", 1)[1].lower().strip()
    parts = dom.split(".")
    if len(parts) < 2:
        return False
    last1 = parts[-1]                 # e.g. "com"
    last2 = parts[-2] + "." + parts[-1]  # e.g. "com.au"
    return (last1 in COMMON_TLDS) or (last2 in COMMON_TLDS)

# ---------- Custom validators ----------


class NameHuman:
    """
    Human name: letters with optional spaces/hyphens/apostrophes.
    Examples: 'Boon Leon', "O'Connor", 'Anne-Marie', 'De la Cruz'
    - No digits allowed
    - Must start and end with a letter
    """
    pattern = re.compile(r"^[A-Za-z](?:[A-Za-z\s'\-]*[A-Za-z])?$")

    def __call__(self, form, field):
        s = (field.data or "").strip()
        if not s:
            return  # InputRequired handles empty
        if not self.pattern.fullmatch(s):
            raise ValidationError(
                "Letters, spaces, hyphens and apostrophes only (e.g., Boon Leon, O'Connor, Anne-Marie).")


class PasswordStrength:
    """
    Require: length >= min_length and at least 3 of 4 classes
    (lowercase / uppercase / digit / symbol). Also forbids using
    first name, surname, or email local-part inside the password.
    """

    def __init__(self, min_length: int = 8):
        self.min_length = min_length

    def __call__(self, form, field):
        pwd = field.data or ""
        if len(pwd) < self.min_length:
            raise ValidationError(
                f"Password must be at least {self.min_length} characters long.")

        classes = sum((
            bool(re.search(r"[a-z]", pwd)),
            bool(re.search(r"[A-Z]", pwd)),
            bool(re.search(r"\d",    pwd)),
            bool(re.search(r"[^\w\s]", pwd)),  # symbol/punctuation
        ))
        if classes < 3:
            raise ValidationError(
                "Use at least three of: lowercase, uppercase, digit, symbol.")

        blocked = [
            (getattr(form, "first_name", None).data or "") if hasattr(
                form, "first_name") else "",
            (getattr(form, "surname",    None).data or "") if hasattr(
                form, "surname") else "",
            ((getattr(form, "email",     None).data or "").split(
                "@")[0]) if hasattr(form, "email") else "",
        ]
        low = pwd.lower()
        for token in blocked:
            t = (token or "").lower().strip()
            if t and len(t) >= 3 and t in low:
                raise ValidationError(
                    "Password must not contain your name or email.")


class AUPhone:
    """AU mobile only: exactly 10 digits after normalization; must start with '04'."""

    def __call__(self, form, field):
        digits = _digits_only(field.data)
        if len(digits) != 10:
            raise ValidationError("Enter a valid 10-digit mobile number.")
        if not re.fullmatch(r"04\d{8}", digits):
            raise ValidationError(
                "Mobile numbers must start with 04 and be 10 digits (e.g., 04XXXXXXXX).")


class AddressStrict:
    """
    Plausible AU street address, e.g. '12 King St', '5/23 O’Connell Rd', '44-46 Main Road'.
    Requires number + street name + common suffix.
    """
    pattern = re.compile(
        r"^(?:\d{1,4}(?:-\d{1,4})?/)?\d{1,5}\s+"
        r"[A-Za-z][A-Za-z\s'.\-]{2,}"
        r"(?:\s+(?:St|Street|Rd|Road|Ave|Avenue|Blvd|Dr|Drive|Ct|Court|Pl|Place|Cres|Crescent|Hwy|Highway))$",
        re.IGNORECASE
    )

    def __call__(self, form, field):
        s = (field.data or "").strip()
        if len(s) < 8 or len(s) > 120 or not self.pattern.fullmatch(s):
            raise ValidationError(
                "Use this format: number + street + suffix (e.g.\u00A0 12 King St \u00A0 OR \u00A0 5/23 O’Connell Rd \u00A0 OR \u00A0 44-46 Main Road)")


class VenueSimple:
    """
    Venue format: '<Venue name>, <City/Suburb>'
    - Exactly two comma-separated parts.
    - First part must include letters (rejects purely numeric).
    - Second part must look like a city/suburb: letters and spaces only.
    """
    has_letter = re.compile(r"[A-Za-z]")
    # e.g., 'Sydney', 'South Brisbane'
    city_re = re.compile(r"^[A-Za-z]+(?:\s+[A-Za-z]+){0,5}$")

    def __call__(self, form, field):
        raw = (field.data or "").strip()
        parts = [p.strip() for p in raw.split(",")]
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValidationError(
                "Use format like 'Town Hall, Sydney' or 'Convention Centre, South Brisbane'.")
        venue_part, city_part = parts
        if not self.has_letter.search(venue_part):
            raise ValidationError(
                "The venue name must include letters (e.g., 'Town Hall').")
        if not self.city_re.fullmatch(city_part):
            raise ValidationError(
                "End with a suburb/city (letters & spaces only), e.g., 'South Brisbane'.")


class VendorNamesStrict:
    """
    One or more vendor names separated by commas or '&'.
    - Allowed: letters, spaces, commas, '&', apostrophes, hyphens.
    - No digits allowed anywhere.
    - Each vendor must contain at least 4 letters in total.
    """
    overall = re.compile(r"^[A-Za-z\s,&'\-]+$")  # no digits

    def __call__(self, form, field):
        s = (field.data or "").strip()
        if not self.overall.fullmatch(s):
            raise ValidationError(
                "Vendor names may use letters, spaces, commas, '&', apostrophes and hyphens only.")
        vendors = [v.strip() for v in re.split(r"[,&]", s) if v.strip()]
        for v in vendors:
            if sum(ch.isalpha() for ch in v) < 4:
                raise ValidationError(
                    "Each vendor name must include at least 4 letters (e.g., 'Alice', 'Bob Jones').")

# ---------- File upload helper ----------


def check_upload_file(form) -> str:
    """Save uploaded image to ./static/img and return the DB-relative path."""
    fp = form.image.data
    filename = secure_filename(fp.filename)
    base_path = os.path.dirname(__file__)
    upload_path = os.path.join(base_path, "static/img", filename)
    db_upload_path = "/static/img/" + filename
    fp.save(upload_path)
    return db_upload_path

# ---------- Forms ----------


class EventForm(FlaskForm):
    """
    Create/Update event form.
    - On create: image is required.
    - On update: image optional (keeps existing if not provided).
    """
    event_id = HiddenField()  # used by duplicate-title check to exclude current row

    title = StringField("Enter Title of this event", validators=[
                        InputRequired()], filters=[_strip])
    description = StringField(
        "Enter Description of this event", validators=[InputRequired()])
    image = FileField("Event Image")  # validators set dynamically in __init__

    start_time = DateTimeLocalField(
        "Start time", format="%Y-%m-%dT%H:%M", validators=[DataRequired()])
    end_time = DateTimeLocalField(
        "End time",   format="%Y-%m-%dT%H:%M", validators=[DataRequired()])

    venue = StringField("Venue", validators=[
                        DataRequired(), VenueSimple()], filters=[_strip])
    vendor_names = StringField(
        "Vendors name",
        validators=[InputRequired(), Length(max=255), VendorNamesStrict()],
        filters=[_strip],
    )

    total_tickets = IntegerField("Total tickets", validators=[DataRequired()])
    ticket_price = DecimalField("Individual ticket price", places=2, validators=[
                                InputRequired(), NumberRange(min=0)])
    free_sampling = BooleanField("Free sampling?")
    provide_takeaway = BooleanField("Provide takeaway?")
    category_type = SelectField("Category", choices=[(
        e.name, e.value) for e in EventCategory], validators=[DataRequired()])

    submit = SubmitField("Create/Update Event")

    def __init__(self, *args, require_image: bool = True, **kwargs):
        """
        Toggle image requirement:
          - require_image=True  -> FileRequired + FileAllowed (create)
          - require_image=False -> FileAllowed only (update)
        """
        super().__init__(*args, **kwargs)
        allowed = FileAllowed(
            ALLOWED_FILE, message="Only supports png, jpg, JPG, PNG")
        if require_image:
            self.image.validators = [FileRequired(
                message="Please upload a Destination Image"), allowed]
        else:
            self.image.validators = [allowed]

    # ---- Field-level validators ----
    def validate_title(self, field):
        """Case-insensitive uniqueness; exclude self on update."""
        normalized = (field.data or "").strip()
        if not normalized:
            return
        q = db.select(Event).where(func.lower(
            Event.title) == normalized.lower())
        if self.event_id.data:
            try:
                q = q.where(Event.id != int(self.event_id.data))
            except ValueError:
                pass
        if db.session.scalar(q):
            raise ValidationError(
                "An event with this title already exists. Please choose a different title.")

    def validate_start_time(self, field):
        """Start time cannot be in the past."""
        start = field.data
        now = datetime.now()
        if start and start <= now:
            raise ValidationError("Start time cannot be in the past.")

    def validate_end_time(self, field):
        """End must be after start, at least 1 hour long, and not in the past."""
        start = self.start_time.data
        end = field.data
        now = datetime.now()
        if start and end:
            if end <= now:
                raise ValidationError("End time cannot be in the past.")
            if end <= start:
                raise ValidationError("End time must be after the start time.")
            if end - start < timedelta(hours=1):
                raise ValidationError(
                    "Event duration must be at least 1 hour.")


class PurchaseTicketForm(FlaskForm):
    tickets_purchased = IntegerField(
        "How many tickets would you like to purchase?", validators=[DataRequired()])
    submit = SubmitField("Confirm Purchase")


class LoginForm(FlaskForm):
    email = StringField("Email Address", validators=[InputRequired(), Email(
        "Please enter a valid email")], filters=[_lower])
    password = PasswordField("Password", validators=[
                             InputRequired("Enter user password")])
    submit = SubmitField("Login")


class RegisterForm(FlaskForm):
    # Names now allow spaces/hyphens/apostrophes (no digits). Extra spaces are collapsed.
    first_name = StringField(
        "First Name",
        validators=[InputRequired(), Length(min=1, max=50), NameHuman()],
        filters=[_strip, _collapse_spaces],
    )
    surname = StringField(
        "Surname",
        validators=[InputRequired(), Length(min=1, max=50), NameHuman()],
        filters=[_strip, _collapse_spaces],
    )

    email = StringField(
        "Email Address",
        validators=[InputRequired(), Email(
            "Please enter a valid email"), Length(max=120)],
        filters=[_lower],
    )

    phone = TelField(
        "Contact Number",
        validators=[InputRequired(
            "Please enter your mobile number"), AUPhone()],
        filters=[_digits_only],
    )

    address = StringField(
        "Street Address",
        validators=[InputRequired(), AddressStrict()],
        filters=[_strip],
    )

    password = PasswordField(
        "Password",
        validators=[
            InputRequired(),
            PasswordStrength(min_length=8),
            EqualTo("confirm", message="Passwords should match"),
        ],
    )
    confirm = PasswordField("Confirm Password")

    submit = SubmitField("Register")

    # Email uniqueness + domain ending guard
    def validate_email(self, field):
        if not _tld_or_sld_ok(field.data):
            raise ValidationError(
                "Please enter an email with a common domain ending (e.g., .com, .org, .com.au).")
        if db.session.scalar(db.select(User).where(User.email == field.data)):
            raise ValidationError("An account already exists with this email.")

    # Phone uniqueness
    def validate_phone(self, field):
        if db.session.scalar(db.select(User).where(User.phone == field.data)):
            raise ValidationError("This mobile number is already registered.")


class CommentForm(FlaskForm):
    contents = TextAreaField(
        "Want to share your thoughts? Post a comment below.", validators=[InputRequired()])
    submit = SubmitField("Post Comment")
