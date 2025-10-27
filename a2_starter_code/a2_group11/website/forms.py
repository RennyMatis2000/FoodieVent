from datetime import datetime, timedelta
from flask_wtf import FlaskForm
from wtforms.fields import (
    TextAreaField, SubmitField, StringField, TelField, IntegerField, SelectField,
    BooleanField, PasswordField, DateTimeLocalField, DecimalField, HiddenField  
)
from wtforms.validators import DataRequired, InputRequired, Length, Email, EqualTo, NumberRange
from wtforms.validators import ValidationError  
from . models import EventCategory, User, Event
from . import db
from flask_wtf.file import FileRequired, FileField, FileAllowed
from flask import flash
from werkzeug.utils import secure_filename
import os
import re  # <-- added
from sqlalchemy import func     

ALLOWED_FILE = {'PNG', 'JPG', 'JPEG', 'png', 'jpg', 'jpeg'}

# -----------------------------
# Normalization helper filters
# -----------------------------
def _strip(s):
    return s.strip() if s else s

def _lower(s):
    return s.lower().strip() if s else s

def _digits_only(s):
    # remove all non-digits
    return re.sub(r"\D", "", s or "")

def _tld_len_ok(addr: str) -> bool:
    """Require a >= 2 character top-level domain (e.g., .com)."""
    parts = addr.rsplit('.', 1)
    return len(parts) == 2 and len(parts[1]) >= 2

# ---------- Option C: common TLD/SLD allowlist ----------
# Common top-level and second-level endings to allow (extend as needed)
COMMON_TLDS = {
    "com","net","org","edu","gov","io","me","ai","dev",
    "co","uk","au","nz","ca","us","de","fr","sg","jp",
    "com.au","net.au","org.au","edu.au","gov.au",
}

def _tld_or_sld_ok(addr: str) -> bool:
    """
    Allow only common domain endings:
    - handles both single TLDs (example.com) and 2-part SLDs (example.com.au)
    """
    if "@" not in addr:
        return False
    dom = addr.split("@", 1)[1].lower().strip()
    parts = dom.split(".")
    if len(parts) < 2:
        return False
    last1 = parts[-1]  # e.g., "com"
    last2 = parts[-2] + "." + parts[-1] if len(parts) >= 2 else ""  # e.g., "com.au"
    return (last1 in COMMON_TLDS) or (last2 in COMMON_TLDS)

# -----------------------------
# Custom validators
# -----------------------------

class NameLettersOnly:
    """
    Only allow ASCII letters A–Z (case-insensitive). No digits, spaces or punctuation.
    """
    pattern = re.compile(r"^[A-Za-z]+$")

    def __call__(self, form, field):
        s = (field.data or "").strip()
        if not s:
            return  # InputRequired handles empty
        if not self.pattern.fullmatch(s):
            raise ValidationError("Letters only (A–Z).")
class PasswordStrength:
    """
    Enforce: length >= min_length and at least 3 of 4 classes (lower/upper/digit/symbol).
    Also rejects if password contains first name, surname, or the email's local-part.
    """
    def __init__(self, min_length=8):
        self.min_length = min_length

    def __call__(self, form, field):
        pwd = field.data or ""
        if len(pwd) < self.min_length:
            raise ValidationError(f"Password must be at least {self.min_length} characters long.")

        classes = 0
        classes += bool(re.search(r"[a-z]", pwd))
        classes += bool(re.search(r"[A-Z]", pwd))
        classes += bool(re.search(r"\d", pwd))
        classes += bool(re.search(r"[^\w\s]", pwd))  # punctuation/symbol

        if classes < 3:
            raise ValidationError("Use at least three of: lowercase, uppercase, digit, symbol.")

        # personal info check (case-insensitive)
        blocked = [
            (getattr(form, "first_name", None).data or "") if hasattr(form, "first_name") else "",
            (getattr(form, "surname", None).data or "") if hasattr(form, "surname") else "",
            ((getattr(form, "email", None).data or "").split("@")[0]) if hasattr(form, "email") else "",
        ]
        low = pwd.lower()
        for token in blocked:
            t = (token or "").lower().strip()
            if t and len(t) >= 3 and t in low:
                raise ValidationError("Password must not contain your name or email.")

class AUPhone:
    """
    AU mobile only:
    - Exactly 10 digits after normalization
    - Must start with '04'
    """
    def __call__(self, form, field):
        digits = _digits_only(field.data)
        if len(digits) != 10 or not digits.isdigit():
            raise ValidationError("Enter a valid 10-digit mobile number.")
        if not re.fullmatch(r"04\d{8}", digits):
            raise ValidationError("Mobile numbers must start with 04 and be 10 digits (e.g., 04XXXXXXXX).")

class AddressBasic:
    """
    Basic street address sanity:
    - Length >= min_length (default 8) and <= max_length
    - Contains at least one letter AND at least one digit
    - Only common address characters allowed
    """
    def __init__(self, min_length=8, max_length=120):
        self.min_length = min_length
        self.max_length = max_length
        # Letters, digits, space and , . - / # ' are allowed
        self.allowed_re = re.compile(r"^[0-9A-Za-z\s,.\-\/#']+$")

    def __call__(self, form, field):
        s = (field.data or "").strip()
        if len(s) < self.min_length:
            raise ValidationError(f"Address must be at least {self.min_length} characters long.")
        if len(s) > self.max_length:
            raise ValidationError(f"Address must be at most {self.max_length} characters long.")
        if not self.allowed_re.fullmatch(s):
            raise ValidationError("Use only letters, numbers, spaces, and , . - / # ' characters.")
        if not re.search(r"[A-Za-z]", s) or not re.search(r"\d", s):
            raise ValidationError("Include a street number and a street name (e.g., '12 King St').")

class AddressStrict:
    """
    Requires a plausible AU-style street address:
    - optional unit prefix: '5/' or '12-14/'
    - street number: 1–5 digits (optionally a range 44-46)
    - at least one space
    - street name (letters & spaces & common punctuation)
    - REQUIRED suffix (St, Street, Rd, Road, Ave, Avenue, Blvd, Dr, Drive, Ct, Court, Pl, Place, Cres, Crescent, Hwy, Highway)
    """
    def __call__(self, form, field):
        s = (field.data or "").strip()
        if len(s) < 8 or len(s) > 120:
            raise ValidationError("Enter a valid street address.")
        pattern = re.compile(
            r"^(?:\d{1,4}(?:-\d{1,4})?/)?\d{1,5}\s+"
            r"[A-Za-z][A-Za-z\s'.\-]{2,}"
            r"(?:\s+(?:St|Street|Rd|Road|Ave|Avenue|Blvd|Dr|Drive|Ct|Court|Pl|Place|Cres|Crescent|Hwy|Highway))$",
            # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            # made suffix REQUIRED by removing the trailing ? above
            re.IGNORECASE,
        )
        if not pattern.fullmatch(s):
            raise ValidationError(
                "Enter a street number, name and suffix (e.g., '12 King St', '5/23 O’Connell Rd', '44-46 Main Road')."
            )

# ---- NEW: simpler venue validator ----
class VenueSimple:
    """
    Very simple venue format:

      '<Venue name>, <City/Suburb>'

    Rules:
      - Exactly 2 comma-separated parts.
      - First part must contain letters (not just digits).
      - Last part must be letters & spaces only (looks like a city/suburb).
    """
    has_letter = re.compile(r"[A-Za-z]")
    city_re    = re.compile(r"^[A-Za-z]+(?:\s+[A-Za-z]+){0,5}$")  # e.g., 'Sydney', 'South Brisbane'

    def __call__(self, form, field):
        raw = (field.data or "").strip()
        if not raw:
            return  # DataRequired handles empty

        parts = [p.strip() for p in raw.split(",")]
        # require exactly 2 parts: '<venue>, <city/suburb>'
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValidationError("Use format like 'Town Hall, Sydney' or 'Convention Centre, South Brisbane'.")

        venue_part, city_part = parts[0], parts[1]

        # first part must contain letters (reject '12345, Sydney')
        if not self.has_letter.search(venue_part):
            raise ValidationError("The venue name must include letters (e.g., 'Town Hall').")

        # last part must look like a suburb/city: letters/spaces only
        if not self.city_re.fullmatch(city_part):
            raise ValidationError("End with a suburb/city (letters & spaces only), e.g., 'South Brisbane'.")

# ---- NEW: strict vendor names validator (no digits, each name >= 4 letters) ----
class VendorNamesStrict:
    """
    Accept one or more vendor names separated by commas or '&'.
    - Allowed chars overall: letters, spaces, commas, &, apostrophes, hyphens.
    - No digits allowed anywhere.
    - Each vendor must contain at least 4 alphabetic letters in total.
    """
    overall = re.compile(r"^[A-Za-z\s,&'\-]+$")  # no digits

    def __call__(self, form, field):
        s = (field.data or "").strip()
        if not s:
            return  # InputRequired handles empty

        if not self.overall.fullmatch(s):
            raise ValidationError("Vendor names may include letters, spaces, commas, '&', apostrophes and hyphens only.")

        # split on commas and ampersands to validate each vendor name
        vendors = [v.strip() for v in re.split(r"[,&]", s) if v.strip()]
        for v in vendors:
            # count letters in the vendor token
            letter_count = sum(ch.isalpha() for ch in v)
            if letter_count < 4:
                raise ValidationError("Each vendor name must include at least 4 letters (e.g., 'Alice', 'Bob Jones').")

def check_upload_file(form):
    # get file data from form
    fp = form.image.data
    filename = fp.filename
    # get the current path of the module file… store image file relative to this path
    BASE_PATH = os.path.dirname(__file__)
    # upload file location – directory of this file/static/image
    upload_path = os.path.join(BASE_PATH,'static/img',secure_filename(filename))
    # store relative path in DB as image location in HTML is relative
    db_upload_path = '/static/img/' + secure_filename(filename)
    # save the file and return the db upload path
    fp.save(upload_path)
    return db_upload_path

# Create an event or update an event
class EventForm(FlaskForm):
    # hidden field so validators can exclude the current row on update
    event_id = HiddenField()  # <-- used in duplicate-title check

    title = StringField('Enter Title of this event', validators=[InputRequired()], filters=[_strip])  # <-- strip
    description = StringField('Enter Description of this event', validators=[InputRequired()])

    # NOTE: we will toggle FileRequired at runtime (create vs update)
    image = FileField('Destination Image')  # validators set in __init__ below

    start_time = DateTimeLocalField("Start time", format="%Y-%m-%dT%H:%M", validators=[DataRequired()])
    end_time   = DateTimeLocalField("End time",   format="%Y-%m-%dT%H:%M", validators=[DataRequired()])

    # <-- NEW: VenueSimple applied here
    venue = StringField("Venue", validators=[DataRequired(), VenueSimple()], filters=[_strip])

    # <-- UPDATED: use VendorNamesStrict (no digits, each >= 4 letters)
    vendor_names = StringField(
        "Vendors name",
        validators=[InputRequired(), Length(max=255), VendorNamesStrict()],
        filters=[_strip],
    )

    total_tickets = IntegerField("Total tickets", validators=[DataRequired()])
    ticket_price  = DecimalField("Individual ticket price", places=2, validators=[InputRequired(), NumberRange(min=0)])
    free_sampling = BooleanField("Free sampling?")
    provide_takeaway = BooleanField("Provide takeaway?")
    category_type = SelectField("Category", choices=[(e.name, e.value) for e in EventCategory], validators=[DataRequired()])

    # Submission button
    submit = SubmitField("Create/Update Event")

    # ---- runtime toggle for image requirement (create=True, update=False) ----
    def __init__(self, *args, require_image: bool = True, **kwargs):
        """
        When require_image=True (create): image must be uploaded.
        When require_image=False (update): image is optional, FileAllowed only.
        """
        super().__init__(*args, **kwargs)
        allowed = FileAllowed(ALLOWED_FILE, message='Only supports png, jpg, JPG, PNG')
        if require_image:
            self.image.validators = [FileRequired(message='Please upload a Destination Image'), allowed]
        else:
            self.image.validators = [allowed]

    # -------- EventForm custom field validators --------
    def validate_title(self, field):
        """No duplicate titles (case-insensitive). Exclude self on update via hidden event_id."""
        normalized = (field.data or "").strip()
        if not normalized:
            return
        q = db.select(Event).where(func.lower(Event.title) == normalized.lower())
        # exclude current row on update
        if self.event_id.data:
            try:
                q = q.where(Event.id != int(self.event_id.data))
            except ValueError:
                pass
        existing = db.session.scalar(q)
        if existing:
            raise ValidationError("An event with this title already exists. Please choose a different title.")
        
    def validate_start_time(self, field):
        """Start time cannot be in the past and must be in the future"""
        start = field.data
        now = datetime.now()
        if start:
            if start <= now:
                raise ValidationError("Start time cannot be in the past.")

    def validate_end_time(self, field):
        """End after start and at least 1 hour duration."""
        start = self.start_time.data
        end = field.data
        now = datetime.now()
        if start and end:
            if end and end <= now:
                raise ValidationError("End time cannot be in the past.")
            if end <= start:
                raise ValidationError("End time must be after the start time.")
            if end - start < timedelta(hours=1):
                raise ValidationError("Event duration must be at least 1 hour.")

# Purchase ticket form
class PurchaseTicketForm(FlaskForm):
    tickets_purchased = IntegerField(f'How many tickets would you like to purchase?', validators=[DataRequired()])

    # Submission button
    submit = SubmitField("Confirm Purchase")

# creates the login information
class LoginForm(FlaskForm):
    email = StringField("Email Address", validators=[InputRequired(), Email("Please enter a valid email")], filters=[_lower])
    password=PasswordField("Password", validators=[InputRequired('Enter user password')])
    submit = SubmitField("Login")

# this is the registration form
class RegisterForm(FlaskForm):
    first_name = StringField(
        "First Name",
        validators=[InputRequired(), Length(min=1, max=50), NameLettersOnly()], 
        filters=[_strip],
    )
    surname = StringField(
        "Surname",
        validators=[InputRequired(), Length(min=1, max=50), NameLettersOnly()], 
        filters=[_strip],
    )
    email = StringField(
        "Email Address",
        validators=[InputRequired(), Email("Please enter a valid email"), Length(max=120)],
        filters=[_lower],
    )
    # Original validator note kept:
    # phone=TelField("Contact Number", validators=[InputRequired("Please enter a valid phone number, which is exactly 10 digits"), Length(min=10, max=10)])
    phone=TelField(
        "Contact Number",
        validators=[InputRequired("Please enter your mobile number"), AUPhone()],
        filters=[_digits_only],
    )
    address=StringField(
        "Street Address",
        # validators=[InputRequired(), AddressBasic(min_length=8, max_length=120)],  # <- original permissive rule
        validators=[InputRequired(), AddressStrict()],  # <- stricter, street-like format (suffix required)
        filters=[_strip],
    )
    # linking two fields - password should be equal to data entered in confirm
    password=PasswordField(
        "Password",
        validators=[
            InputRequired(),
            PasswordStrength(min_length=8),
            EqualTo('confirm', message="Passwords should match")
        ]
    )
    confirm = PasswordField("Confirm Password")

    # submit button
    submit = SubmitField("Register")

    # ---- DB uniqueness check for email (with common TLD/SLD allowlist) ----
    def validate_email(self, field):
        # Basic syntax is already checked by WTForms' Email()
        # Restrict to common endings to catch obvious typos like '.coddddd'
        if not _tld_or_sld_ok(field.data):
            raise ValidationError("Please enter an email with a common domain ending (e.g., .com, .org, .com.au).")

        existing = db.session.scalar(db.select(User).where(User.email == field.data))
        if existing:
            raise ValidationError("An account already exists with this email.")

    # ---- DB uniqueness check for phone (digits-only) ----
    def validate_phone(self, field):
        existing = db.session.scalar(db.select(User).where(User.phone == field.data))
        if existing:
            raise ValidationError("This mobile number is already registered.")

# Create a user comment
class CommentForm(FlaskForm):
    contents = TextAreaField('Comment', validators=[InputRequired('Want to share your thoughts? Post a comment here')])
    submit = SubmitField('Create')

# Create an order form
# class OrderForm(FlaskForm):
