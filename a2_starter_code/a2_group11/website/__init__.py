# Import flask and associated modules with flask
from flask import Flask, render_template
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Create the database using SQLAlchemy
db = SQLAlchemy()

# Create a function that creates a web application, a web server will run on this application
def create_app():
  
   app = Flask(__name__)  # This is the name of the module/package that is calling this app
   # As the website is in a production environment, debug is set to False
   app.debug = True
   app.secret_key = 'somesecretkey'
   # Set the app configuration data 
   app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sitedata.sqlite'
   # Initialise db with flask app
   db.init_app(app)

   Bootstrap5(app)
   
   # initialise the login manager
   login_manager = LoginManager()
   
   # set the name of the login function that lets user login
   # in our case it is auth.login (blueprintname.viewfunction name)
   login_manager.login_view = 'auth.login'
   login_manager.init_app(app)

# Config upload folder
   UPLOAD_FOLDER = 'static/img'
   app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

   # Create a user loader function takes userid and returns User
   # Importing inside the create_app function avoids circular references
   from .models import User
   @login_manager.user_loader
   def load_user(user_id):
      return db.session.scalar(db.select(User).where(User.id==user_id))
   
   # Inbuilt function for handling 404 errors
   @app.errorhandler(404) 
   def not_found(e): 
      return render_template("404.html", error=e)
   
   # Inbuilt function for handling 500 errors
   @app.errorhandler(500)
   def server_error(e):
    # Rollback the database for database safety in the event of a 500 error
    db.session.rollback()
    return render_template("500.html", error=e)

   # Import main blueprints, handling the main views of the website
   from . import views
   app.register_blueprint(views.main_bp)

   # Import authentication blueprints
   from . import auth
   app.register_blueprint(auth.auth_bp)

   # Import event blueprints, handling event related views
   from . import events
   app.register_blueprint(events.event_bp)

   # Import user blueprints, handling views only a logged in user can see
   from . users import user_bp
   app.register_blueprint(user_bp)

   # Import order blueprints, handling blueprints related to orders
   from .orders import order_bp
   app.register_blueprint(order_bp)
   
   return app