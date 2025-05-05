from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, EmailField, SelectField, FileField,IntegerField,TimeField ,DateField ,SubmitField,DateTimeLocalField,TextAreaField , DateTimeField, FloatField
from wtforms.validators import DataRequired, Length, Email, EqualTo,NumberRange,Optional
from flask_wtf.file import FileAllowed

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', choices=[('petowner', 'Pet Owner'), ('vet', 'Vet'), ('admin', 'Admin')], validators=[DataRequired()])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])


class PetForm(FlaskForm):
    name = StringField('Pet Name', validators=[DataRequired()])
    species = StringField('Species', validators=[DataRequired()])
    breed = StringField('Breed', validators=[DataRequired()])
    
    registration_date = DateField('Registration Date', format='%Y-%m-%d', validators=[DataRequired()])
    age_years = IntegerField('Age (Years)', default=None)  # Allow integer input for years
    age_months = IntegerField('Age (Months)', default=None)  # Allow integer input for months
    photo = FileField('Pet Photo', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif'])])
    submit = SubmitField('Register Pet')

# Define a form using Flask-WTF

class HealthRecordForm(FlaskForm):
    pet_name = StringField('Pet Name', validators=[DataRequired()])
    weight = FloatField('Weight (kg)', validators=[Optional(), NumberRange(min=0)])
    temperature = FloatField('Temperature (°C)', validators=[Optional(), NumberRange(min=0)])
    diagnosis = TextAreaField('Diagnosis', validators=[DataRequired()])
    treatment = TextAreaField('Treatment', validators=[DataRequired()])
    comments = TextAreaField('Comments', validators=[Optional()])
    submit = SubmitField('Submit')

class AppointmentForm(FlaskForm):
    pet_id = SelectField('Pet', coerce=int, validators=[DataRequired()])
    vet_id = SelectField('Vet', coerce=int, validators=[DataRequired()])
    appointment_date = DateTimeLocalField('Date and Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    reason = TextAreaField('Reason for the Appointment', validators=[DataRequired()])
    submit = SubmitField('Book Appointment')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # You can also dynamically populate the SelectField choices with pets and vets in your view
    def populate_pets(self, pets):
        self.pet_id.choices = [(pet.id, pet.name) for pet in pets]

    def populate_vets(self, vets):
        self.vet_id.choices = [(vet.id, vet.username) for vet in vets]


class VaccinationReminderForm(FlaskForm):
    pet_id = SelectField('Select Pet', coerce=int, validators=[DataRequired()])
    vaccine_type = StringField('Vaccination Type', validators=[DataRequired()])
    reminder_date = DateField('Date', validators=[DataRequired()])
    reminder_time = TimeField('Time', validators=[DataRequired()])
    submit = SubmitField('Set Reminder')