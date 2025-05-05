from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    pets = db.relationship('Pet', backref='owner', lazy=True)

    def __repr__(self):
        return f"<User {self.username}>"

class Pet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    species = db.Column(db.String(100), nullable=False)
    breed = db.Column(db.String(100), nullable=False)
    color = db.Column(db.String(50), nullable=False)
    age_years = db.Column(db.Integer, nullable=False)
    age_months = db.Column(db.Integer, nullable=False)
    registration_date = db.Column(db.Date, default=datetime.utcnow)
    photo = db.Column(db.String(150))
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"<Pet {self.name}>"
