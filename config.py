import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_secret_key'
    UPLOAD_FOLDER = 'static/uploads'
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
    # Update this line with XAMPP MySQL credentials
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost/pet_health_2'  # root is default user, no password
    SQLALCHEMY_TRACK_MODIFICATIONS = False
