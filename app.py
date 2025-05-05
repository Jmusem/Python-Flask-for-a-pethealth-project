import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import uuid
from flask import Flask, render_template, redirect, url_for, flash, session, request,jsonify,json ,send_file
from flask_login import LoginManager, login_user, login_required, logout_user, current_user,UserMixin
from werkzeug.utils import secure_filename
import pymysql,mysql
from fpdf import FPDF
import requests
from mpesa import lipa_na_mpesa
import base64
from werkzeug.security import check_password_hash
from datetime import datetime
from requests.auth import HTTPBasicAuth
from email.message import EmailMessage
import os
from forms import RegisterForm,LoginForm, PetForm,AppointmentForm ,HealthRecordForm, VaccinationReminderForm
from datetime import datetime ,timedelta
from io import BytesIO
from flask_mail import Mail, Message
# Initialize Flask app
app = Flask(__name__)

# Flask configuration
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'jpg', 'jpeg', 'png', 'gif'}
# Initialize Mail object
mail = Mail(app)
# MySQL database connection

MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = 'musembijoshua40@gmail.com'
MAIL_PASSWORD = '@Joshua6789'
MAIL_DEFAULT_SENDER = 'musembijoshua40@gmail.com'
    # Re-establish the connection if needed
connection = pymysql.connect(
        host='localhost',
        user='root',
        password='',
        database='pet_health_2',
        cursorclass=pymysql.cursors.DictCursor
    )

def check_connection(connection):
    try:
        # Check if the connection is alive
        connection.ping(reconnect=True)
    except pymysql.MySQLError as e:
        print(f"Error reconnecting to the database: {e}")
        return False
    return
# Flask-Login setup
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Helper function for allowed file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

class User(UserMixin):
    def __init__(self, id, username, email, role):
        self.id = id
        self.username = username
        self.email = email
        self.role = role

    def get_id(self):
        return str(self.id)
# User loader function for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user_data = cursor.fetchone()

        # If user data is found, return an instance of the User class
        if user_data:
            return User(
                id=user_data['id'],
                username=user_data['username'],
                email=user_data['email'],
                role=user_data['role']
            )
        return None  # Return None if no user is found
    except Exception as e:
        print(f"Error loading user: {e}")
        return None
# Index Route
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    # Check if the user is an admin
    if session.get('user_role') != 'admin':
        flash("Access denied! Admins only.", "danger")
        return redirect(url_for('login'))

    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            # Fetch total counts
            cursor.execute("SELECT COUNT(*) AS total_users FROM users")
            total_users = cursor.fetchone()['total_users']

            cursor.execute("SELECT COUNT(*) AS total_pets FROM pets")
            total_pets = cursor.fetchone()['total_pets']

            cursor.execute("SELECT COUNT(*) AS total_appointments FROM appointments")
            total_appointments = cursor.fetchone()['total_appointments']

            # Fetch all user details
            cursor.execute("SELECT id, username, email, role, created_at FROM users")
            users = cursor.fetchall()

            # Fetch all pet details (ensure correct column names)
            cursor.execute("SELECT id, name, species, breed, age_years, age_months, registration_date FROM pets")
            pets = cursor.fetchall()

            # Fetch all appointments
            cursor.execute("SELECT id, pet_id, vet_id, appointment_date FROM appointments")
            appointments = cursor.fetchall()

        return render_template("admin_dashboard.html",
                               total_users=total_users,
                               total_pets=total_pets,
                               total_appointments=total_appointments,
                               users=users,
                               pets=pets,
                               appointments=appointments)

    except pymysql.MySQLError as e:
        flash(f"Database error: {e.args[1]}", "danger")
        return redirect(url_for('login'))


@app.route('/delete_user/<int:user_id>')
@login_required
def delete_user(user_id):
    if session.get('user_role') != 'admin':
        flash("Access denied!", "danger")
        return redirect(url_for('admin_dashboard'))

    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            connection.commit()
            flash("User deleted successfully!", "success")
    except pymysql.MySQLError as e:
        flash(f"Database error: {e.args[1]}", "danger")

    return redirect(url_for('admin_dashboard'))


# Database connection settings
db_config = {
    "host": "localhost",
    "user": "root",  # default MySQL user for XAMPP
    "password": "",  # default password for XAMPP MySQL
    "database": "pet_health_2",  # Your database name
}

# Route to manage users
@app.route('/manage_users')
def manage_users():
    try:
        # Establish connection to the database
        connection = pymysql.connect(**db_config)
        cursor = connection.cursor()

        # Query to fetch all users
        cursor.execute("SELECT id, username, email, role, created_at FROM users")
        users = cursor.fetchall()  # Fetch all rows

        # Pass users to the template
        return render_template('manage_users.html', users=users)

    except pymysql.MySQLError as e:
        print(f"Error: {e}")
        return "There was an error fetching the users from the database."

    finally:
        if connection:
            connection.close()  # Close the connection when done


@app.route('/consultation', methods=['GET', 'POST'])
def consultation():
    if request.method == 'POST':
        pet_id = request.form['pet_id']
        vet_id = request.form['vet_id']
        description = request.form['description']
        pet_owner_id = session['user_id']  # Assuming user is logged in

        # Save to database
        cursor = connection.cursor()
        sql = "INSERT INTO consultations (pet_owner_id, pet_id, vet_id, description) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (pet_owner_id, pet_id, vet_id, description))
        connection.commit()
        cursor.close()

        flash('Consultation submitted successfully!')
        return redirect(url_for('consultation'))

    # Otherwise (GET)
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    # Fetch user's pets
    cursor.execute("SELECT id, name FROM pets WHERE owner_id = %s", (session['user_id'],))
    pets = cursor.fetchall()

    # Fetch vets
    cursor.execute("SELECT id, username FROM users WHERE role = 'vet'")
    vets = cursor.fetchall()

    cursor.close()

    return render_template('consultation.html', pets=pets, vets=vets)

@app.route('/delete_pet/<int:pet_id>')
@login_required
def delete_pet(pet_id):
    if session.get('user_role') != 'admin':
        flash("Access denied!", "danger")
        return redirect(url_for('admin_dashboard'))

    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM pets WHERE id = %s", (pet_id,))
            connection.commit()
            flash("Pet deleted successfully!", "success")
    except pymysql.MySQLError as e:
        flash(f"Database error: {e.args[1]}", "danger")

    return redirect(url_for('admin_dashboard'))


@app.route('/delete_appointment/<int:appointment_id>')
@login_required
def delete_appointment(appointment_id):
    if session.get('user_role') != 'admin':
        flash("Access denied!", "danger")
        return redirect(url_for('admin_dashboard'))

    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM appointments WHERE id = %s", (appointment_id,))
            connection.commit()
            flash("Appointment canceled!", "success")
    except pymysql.MySQLError as e:
        flash(f"Database error: {e.args[1]}", "danger")

    return redirect(url_for('admin_dashboard'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    try:
        # Ensure database connection is open
        if not connection.open:
            connection.ping(reconnect=True)

        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT COUNT(*) AS admin_count FROM users WHERE role = 'admin'")
            admin_count = cursor.fetchone()['admin_count']

    except pymysql.MySQLError as e:
        flash(f"Database error: {e.args[1]}", "danger")
        return redirect(url_for('register'))

    # Allow first user to be an admin
    allow_admin_creation = admin_count == 0

    # Ensure only admins can assign roles (except first admin)
    if 'user_role' in session and session['user_role'] != 'admin' and not allow_admin_creation:
        flash("Only admins can assign roles.", "danger")
        return redirect(url_for('dashboard'))

    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data  # ⚠ Stored in plain text (NOT SECURE)
        role = form.role.data

        try:
            with connection.cursor() as cursor:
                # Allow only first user to be an admin or existing admins to create admins
                if role == 'admin' and not allow_admin_creation and session.get('user_role') != 'admin':
                    flash("You are not authorized to create an admin account.", "danger")
                    return redirect(url_for('register'))

                cursor.execute(
                    "INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s)",
                    (username, email, password, role)
                )
                connection.commit()

            flash('Account created successfully! You can now log in.', 'success')
            return redirect(url_for('login'))

        except pymysql.MySQLError as e:
            flash(f"Database error: {e.args[1]}", "danger")
            print(f"Database error: {e.args[0]}, {e.args[1]}")

    return render_template('register.html', form=form, allow_admin_creation=allow_admin_creation)

# Login Route

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data  # ⚠ Plain-text password

        try:
            # Ensure database connection is open
            if not connection.open:
                connection.ping(reconnect=True)

            # Fetch user from database
            with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
                user = cursor.fetchone()

            # Direct password comparison (⚠ Not secure)
            if user and user['password'] == password:
                user_obj = User(
                    id=user['id'],
                    username=user['username'],
                    email=user['email'],
                    role=user['role']
                )
                login_user(user_obj)  # Log the user in
                session['user_role'] = user['role']  # Store role in session
                flash('Login successful!', 'success')

                # Redirect based on role
                if user['role'] == 'admin':
                    return redirect(url_for('admin_dashboard'))
                elif user['role'] == 'vet':
                    return redirect(url_for('vet_dashboard'))
                elif user['role'] == 'petowner':
                    return redirect(url_for('petowner_dashboard'))
                else:
                    flash("Unknown role. Please contact support.", "danger")
                    return redirect(url_for('login'))

            flash('Invalid email or password.', 'danger')

        except pymysql.MySQLError as e:
            flash(f"Database error: {e.args[0]}, {e.args[1]}", 'danger')
        except Exception as e:
            flash(f"An unexpected error occurred: {e}", 'danger')

    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Petowner Dashboard
@app.route('/petowner_dashboard')
@login_required
def petowner_dashboard():
    # Ensure username is correctly retrieved
    username = session.get('username') or current_user.username  # Use session or Flask-Login's current_user
    
    if not username:
        return redirect(url_for('login'))  # Redirect if no username found

    return render_template('petowner_dashboard.html', username=username)
# Vet Dashboard
@app.route('/vet_dashboard')
@login_required
def vet_dashboard():
    return render_template('vet_dashboard.html', username=session.get('username'))

# Register Pet Route
@app.route('/register_pets', methods=['GET', 'POST'])
@login_required  # Ensure user is logged in before accessing the route
def register_pets():
    form = PetForm()
    if form.validate_on_submit():
        name = form.name.data
        species = form.species.data
        breed = form.breed.data
        registration_date = form.registration_date.data
        age_years = form.age_years.data
        age_months = form.age_months.data
        photo = form.photo.data

        # Check if photo is uploaded and save it
        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(photo_path)
        else:
            photo_path = None

        # Insert pet data into the database using current_user.id
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO pets (name, species, breed, registration_date, age_years, age_months, photo, owner_id) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (name, species, breed, registration_date, age_years, age_months, photo_path, current_user.id)
            )
            connection.commit()

        flash('Pet registered successfully!', 'success')
        return redirect(url_for('manage_pets'))

    return render_template('register_pets.html', form=form)

# Manage Pets Route
@app.route('/manage_pets')
@login_required
def manage_pets():
    # Fetch pets for the currently logged-in user
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM pets WHERE owner_id = %s", (current_user.id,))
        pets = cursor.fetchall()

    return render_template('manage_pets.html', pets=pets)



# Initialize OpenAI with your API key
  # Replace with your actual API key



def send_email(recipient_email, subject, body):
    smtp_server = 'smtp.gmail.com'
    port = 587  # TLS port

    sender_email = 'ronalkipro18@gmail.com'  # Replace with your Gmail email address
    sender_password = 'dwdb hprw nhbe qhhf'  # Replace with your Gmail app password

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = recipient_email

    try:
        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls()  # Start TLS encryption
            server.login(sender_email, sender_password)  # Login to the SMTP server
            server.send_message(msg)  # Send the email
            return "Email sent successfully"
    except smtplib.SMTPAuthenticationError:
        return "Error: Authentication failed. Check your credentials."
    except smtplib.SMTPException as e:
        return f"SMTP error occurred: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"
    




@app.route("/mpesa_payment")
def mpesa_payment():
    return render_template("mpesa_payment.html")  


@app.route('/book_appointment', methods=['GET', 'POST'])
@login_required
def book_appointment():
    form = AppointmentForm()

    # Fetch pets and vets
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, name FROM pets WHERE owner_id = %s", (current_user.id,))
        pets = cursor.fetchall()
        cursor.execute("SELECT id, username, email FROM users WHERE role = 'vet'")
        vets = cursor.fetchall()

    form.pet_id.choices = [(pet['id'], pet['name']) for pet in pets]
    form.vet_id.choices = [(vet['id'], vet['username']) for vet in vets]

    available_slots = []

    if form.validate_on_submit():
        pet_id = form.pet_id.data
        vet_id = form.vet_id.data
        appointment_date = form.appointment_date.data
        reason = form.reason.data

        current_datetime = datetime.now()

        # **RESTRICTION 1:** Ensure appointment is not in the past
        if appointment_date < current_datetime:
            flash('You cannot book an appointment in the past.', 'danger')
            return redirect(url_for('book_appointment'))

        # **RESTRICTION 2:** If booking today, ensure time is in the future
        if appointment_date.date() == current_datetime.date() and appointment_date.time() < current_datetime.time():
            flash('You cannot select a past time for today.', 'danger')
            return redirect(url_for('book_appointment'))

        # **RESTRICTION 3:** Check if the selected vet already has an appointment at that date and time
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS count FROM appointments WHERE vet_id = %s AND appointment_date = %s",
                (vet_id, appointment_date)
            )
            result = cursor.fetchone()
            if result['count'] > 0:
                flash('This time slot is already booked. Please choose a different time.', 'danger')
                return redirect(url_for('book_appointment'))

        # Insert the new appointment into the database with status 'pending'
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO appointments (pet_id, vet_id, appointment_date, reason) "
                "VALUES (%s, %s, %s, %s)",
                (pet_id, vet_id, appointment_date, reason)
            )
            connection.commit()

        # Fetch pet name, vet name, and vet email
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM pets WHERE id = %s", (pet_id,))
            pet_name = cursor.fetchone()['name']
            cursor.execute("SELECT username, email FROM users WHERE id = %s", (vet_id,))
            vet_data = cursor.fetchone()
            vet_name = vet_data['username']
            vet_email = vet_data['email']

        # Fetch current user email
        with connection.cursor() as cursor:
            cursor.execute("SELECT email FROM users WHERE id = %s", (current_user.id,))
            user_email = cursor.fetchone()['email']

        # Email content
        subject = "Appointment Confirmation"
        body_user = f"""
        Appointment Confirmation

        Dear {current_user.username},

        Your appointment has been successfully booked!

        Appointment Details:
        Pet Name: {pet_name}
        Vet Name: {vet_name}
        Appointment Date: {appointment_date.strftime('%Y-%m-%d %H:%M')}
        Reason: {reason}

        Thank you for using our service!
        """
        body_vet = f"""
        Appointment Notification

        Dear {vet_name},

        A new appointment has been booked with you!

        Appointment Details:
        Pet Name: {pet_name}
        Appointment Date: {appointment_date.strftime('%Y-%m-%d %H:%M')}
        Reason: {reason}

        Please prepare accordingly.
        """

        # Send emails to both the user and the vet
        email_status_user = send_email(user_email, subject, body_user)
        email_status_vet = send_email(vet_email, subject, body_vet)

        # Flash messages for email success/failure
        if "Email sent successfully" in email_status_user and "Email sent successfully" in email_status_vet:
            flash('Appointment booked successfully, and confirmation emails sent!', 'success')
        else:
            flash('Appointment booked successfully, but there was an issue sending one or more emails.', 'warning')

        # Redirect to the view appointments page
        return redirect(url_for('view_appointments'))

    return render_template('book_appointment.html', form=form, pets=pets, vets=vets, available_slots=available_slots)
from flask import jsonify
import pymysql

@app.route('/get_booked_slots/<int:vet_id>')
def get_booked_slots(vet_id):
    current_time = datetime.now()  # Get current date & time

    conn = pymysql.connect(host='localhost', user='root', password='', database='pet_health_2')
    cursor = conn.cursor()

    # Fetch only future appointments
    query = "SELECT appointment_date FROM appointments WHERE vet_id = %s AND appointment_date > %s"
    cursor.execute(query, (vet_id, current_time))

    booked_slots = [row[0].strftime('%Y-%m-%dT%H:%M') for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    return jsonify(booked_slots)
@app.route('/view_appointments')
@login_required
def view_appointments():
    with connection.cursor() as cursor:
        if current_user.role == 'petowner':
            # Pet owners see their own appointments
            cursor.execute("""
                SELECT a.id, p.name AS pet_name, u.username AS vet_name, 
                       a.appointment_date, a.reason
                FROM appointments a
                JOIN pets p ON a.pet_id = p.id
                JOIN users u ON a.vet_id = u.id  -- Get assigned vet details
                WHERE p.owner_id = %s
                ORDER BY a.appointment_date
            """, (current_user.id,))
        elif current_user.role == 'vet':
            # Vets see appointments assigned to them
            cursor.execute("""
                SELECT a.id, p.name AS pet_name, po.username AS owner_name, 
                       a.appointment_date, a.reason
                FROM appointments a
                JOIN pets p ON a.pet_id = p.id
                JOIN users po ON p.owner_id = po.id  -- Get pet owner details
                WHERE a.vet_id = %s
                ORDER BY a.appointment_date
            """, (current_user.id,))
        else:
            flash("Unauthorized access!", "danger")
            return redirect(url_for('dashboard'))

        appointments = cursor.fetchall()

    # Format the appointment date
    for appointment in appointments:
        appointment['formatted_date'] = appointment['appointment_date'].strftime('%Y-%m-%d %H:%M')

    return render_template('view_appointments.html', appointments=appointments)


@app.route('/mark_completed/<int:appointment_id>')
def mark_completed(appointment_id):
    # Logic to mark an appointment as completed
    return redirect(url_for('dashboard'))

@app.route('/send_confirmation_email/<int:appointment_id>', methods=['POST'])
@login_required
def send_confirmation_email(appointment_id):
    # Fetch the appointment details from the database using the appointment_id
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM appointments WHERE id = %s", (appointment_id,))
        appointment = cursor.fetchone()

        if appointment:
            # Compose email content
            subject = "Appointment Confirmation"
            body = f"""
            Confirmation Email

            Appointment Details:
            Pet Name: {appointment['pet_name']}
            Vet Name: {appointment['vet_name']}
            Appointment Date: {appointment['appointment_date']}
            Reason: {appointment['reason']}
            """

            # Try sending the email and handle success/failure
            email_status = send_email(current_user.email, subject, body)

            if "Email sent successfully" in email_status:
                flash('Confirmation email sent successfully!', 'success')
            else:
                flash(f'Failed to send email: {email_status}', 'danger')

            return redirect(url_for('view_appointments'))

    flash('Appointment not found or invalid. Please try again.', 'danger')
    return redirect(url_for('view_appointments'))


@app.route('/update_appointment_status/<int:appointment_id>', methods=['POST'])
@login_required
def update_appointment_status(appointment_id):
    if current_user.role != 'vet':
        flash("Unauthorized action!", "danger")
        return redirect(url_for('view_appointments'))

    new_status = request.form.get('status')

    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE appointments 
            SET status = %s 
            WHERE id = %s AND vet_id = %s
        """, (new_status, appointment_id, current_user.id))
        connection.commit()

    flash("Appointment status updated successfully!", "success")
    return redirect(url_for('view_appointments'))

@app.route('/cancel_appointment/<int:appointment_id>', methods=['POST'])
@login_required
def cancel_appointment(appointment_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE appointments SET status = 'cancelled' WHERE id = %s
        """, (appointment_id,))
        connection.commit()

    flash('Appointment cancelled successfully', 'danger')
    return redirect(url_for('view_appointments'))



@app.route('/view_health_records')
def view_health_records():
    # Fetch health records from the database
    try:
        connection = pymysql.connect(host='localhost',
                                      user='root',
                                      password='',
                                      database='pet_health_2', 
                                      cursorclass=pymysql.cursors.DictCursor)
        cursor = connection.cursor()
        
        # Query to fetch health records
        cursor.execute("SELECT * FROM health_records")  # Adjust the query to fit your table structure
        health_records = cursor.fetchall()  # Fetch all records

    except Exception as e:
        flash(f"Error fetching health records: {e}", 'danger')
        health_records = []
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

    return render_template('view_health_records.html', health_records=health_records)


@app.route('/generate_health_report/<int:health_record_id>', methods=['GET'])
@login_required
def generate_health_report(health_record_id):
    try:
        # Reinitialize the connection to ensure it's fresh
        connection = pymysql.connect(host='localhost',
                                      user='root',
                                      password='',
                                      database='pet_health_2',
                                      cursorclass=pymysql.cursors.DictCursor)
        
        with connection.cursor() as cursor:
            # Fetch health record details
            cursor.execute("""
                SELECT hr.id, hr.pet_name, hr.weight, hr.temperature, hr.diagnosis, hr.treatment, hr.comments, hr.created_at
                FROM health_records hr
                WHERE hr.id = %s
            """, (health_record_id,))
            
            health_record = cursor.fetchone()

            if not health_record:
                return "Health record not found.", 404

    except pymysql.MySQLError as e:
        flash(f"Error fetching health record: {e}", 'danger')
        return "Error fetching health record", 500
    finally:
        # Ensure connection is closed after use
        if connection:
            connection.close()

    # Create PDF report
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    
    # Header
    pdf.set_fill_color(200, 220, 255)  # Light blue background
    pdf.cell(200, 10, "Health Record Report", ln=True, align='C', fill=True)
    
    pdf.ln(10)  # Space

    # Pet Details Section
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(50, 10, "Pet Name:", border=1)
    pdf.set_font('Arial', '', 12)
    pdf.cell(140, 10, health_record['pet_name'], border=1, ln=True)

    pdf.set_font('Arial', 'B', 12)
    pdf.cell(50, 10, "Weight (kg):", border=1)
    pdf.set_font('Arial', '', 12)
    pdf.cell(140, 10, str(health_record['weight']), border=1, ln=True)

    pdf.set_font('Arial', 'B', 12)
    pdf.cell(50, 10, "Temperature (°C):", border=1)
    pdf.set_font('Arial', '', 12)
    pdf.cell(140, 10, str(health_record['temperature']), border=1, ln=True)

    pdf.set_font('Arial', 'B', 12)
    pdf.cell(50, 10, "Diagnosis:", border=1)
    pdf.set_font('Arial', '', 12)
    pdf.multi_cell(140, 10, health_record['diagnosis'], border=1)

    pdf.set_font('Arial', 'B', 12)
    pdf.cell(50, 10, "Treatment:", border=1)
    pdf.set_font('Arial', '', 12)
    pdf.multi_cell(140, 10, health_record['treatment'], border=1)

    pdf.set_font('Arial', 'B', 12)
    pdf.cell(50, 10, "Comments:", border=1)
    pdf.set_font('Arial', '', 12)
    pdf.multi_cell(140, 10, health_record['comments'], border=1)

    pdf.ln(10)  # Space before footer

    # Footer
    pdf.set_font('Arial', 'I', 10)
    pdf.cell(0, 10, "Generated on: " + str(health_record['created_at']), ln=True, align='C')

    # ✅ Convert PDF to BytesIO properly
    pdf_output = BytesIO()
    pdf_bytes = pdf.output(dest='S').encode('latin1')  # Convert to bytes
    pdf_output.write(pdf_bytes)
    pdf_output.seek(0)  # Reset buffer position

    return send_file(pdf_output, as_attachment=True, download_name=f"health_record_{health_record['id']}.pdf", mimetype='application/pdf')

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

@app.route('/set_vaccination_reminder', methods=['GET', 'POST'])
@login_required
def set_vaccination_reminder():
    form = VaccinationReminderForm()

    # Fetch registered pets from the database
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, name FROM pets WHERE owner_id = %s", (current_user.id,))
        pets = cursor.fetchall()

    # Populate pet choices
    form.pet_id.choices = [(pet['id'], pet['name']) for pet in pets]

    if request.method == 'POST':
        print("Form Data:", request.form)

        if form.validate_on_submit():
            pet_id = form.pet_id.data
            vaccine_type = form.vaccine_type.data
            reminder_date = form.reminder_date.data   # Date object
            reminder_time = form.reminder_time.data   # Time object

            # Combine date and time into one datetime object
            reminder_datetime = datetime.combine(reminder_date, reminder_time)
            
            # Insert into database using the correct column names
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO vaccination_reminders (pet_id, vaccine_type, reminder_datetime)
                    VALUES (%s, %s, %s)
                """, (pet_id, vaccine_type, reminder_datetime))
                connection.commit()

            # Fetch pet name for confirmation email
            with connection.cursor() as cursor:
                cursor.execute("SELECT name FROM pets WHERE id = %s", (pet_id,))
                pet = cursor.fetchone()
                pet_name = pet['name'] if pet else 'Unknown Pet'

            # Send confirmation email
            recipient_email = current_user.email
            subject = "Vaccination Reminder Confirmation"
            body = f"""
Hello {current_user.username},

Your vaccination reminder has been successfully set.

Pet Name: {pet_name}
Vaccination Type: {vaccine_type}
Reminder Date & Time: {reminder_datetime.strftime('%Y-%m-%d %H:%M:%S')}

Thank you for using our system.

Best regards,
Pet Health Management Team
"""
            send_email(recipient_email, subject, body)

            return redirect(url_for('view_vaccination_reminders'))
        else:
            print("Form validation failed")
            for field, errors in form.errors.items():
                print(f"{field}: {errors}")

    return render_template('set_vaccination_reminder.html', form=form)

@app.route('/send_email_to_vet/<int:appointment_id>', methods=['POST'])
@login_required
def send_email_to_vet(appointment_id):
    # Get the appointment details
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT a.id, p.name AS pet_name, u.username AS vet_name, u.email AS vet_email, a.appointment_date
            FROM appointments a
            JOIN pets p ON a.pet_id = p.id
            JOIN users u ON a.vet_id = u.id
            WHERE a.id = %s
        """, (appointment_id,))
        appointment = cursor.fetchone()

    if not appointment:
        flash('Appointment not found!', 'danger')
        return redirect(url_for('view_appointments'))

    # Compose the email content
    pet_name = appointment['pet_name']
    vet_name = appointment['vet_name']
    vet_email = appointment['vet_email']
    appointment_date = appointment['appointment_date']
    
    subject = f"Appointment Reminder for {pet_name}"
    body = f"Dear Dr. {vet_name},\n\nThis is a reminder for the upcoming appointment with {pet_name} on {appointment_date}.\n\nThank you."

    # Create the email message
    msg = Message(subject, recipients=[vet_email])
    msg.body = body

    # Send the email
    try:
        mail.send(msg)
        flash('Email sent to the vet successfully!', 'success')
    except Exception as e:
        flash(f'Error sending email: {str(e)}', 'danger')

    return redirect(url_for('view_appointments'))

# Function to generate a video meeting link (Example using Jitsi Meet)

@app.route('/book_consultation', methods=['GET', 'POST'])
def book_consultation():
    if request.method == 'POST':
        recipient_email = request.form['recipient_email']
        payment_status = request.form.get('payment_status')

        if payment_status != 'paid':
            flash('Payment is required before booking!', 'danger')
            return redirect(url_for('book_consultation'))

        send_email(recipient_email, "Consultation Request", "Your email consultation has been scheduled.")
        flash("Email consultation booked!", 'success')

        return redirect(url_for('dashboard'))  # Redirect to a confirmation page

    return render_template('book_consultation.html')

# M-Pesa API credentials
CONSUMER_KEY = "Fqba1SNgArfzYF64qY2tzCUMsoNMYeW0TOrwGqhDoZ6bEqx0"
CONSUMER_SECRET = "ITmg99pbD0peUQ27PoMvQU6pFiwNg8OK7Pt86GvGgTRtU56WYIBawrABUPFiBbCb"
BUSINESS_SHORTCODE = "174379"
PASSKEY = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"
CALLBACK_URL = "https://your-ngrok-url.com/callback"  # Update with actual callback URL

# Generate Access Token
def get_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(url, auth=(CONSUMER_KEY, CONSUMER_SECRET))
    return response.json().get("access_token")

# Send STK Push Request
def send_stk_push(phone_number, amount):
    access_token = get_access_token()
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(f"{BUSINESS_SHORTCODE}{PASSKEY}{timestamp}".encode()).decode()
    
    url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    payload = {
        "BusinessShortCode": BUSINESS_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone_number,
        "PartyB": BUSINESS_SHORTCODE,
        "PhoneNumber": phone_number,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": "PetHealth",
        "TransactionDesc": "Pet Health Payment"
    }

    response = requests.post(url, json=payload, headers=headers)
    return response.json()

@app.route("/pay", methods=["POST"])
def pay():
    phone_number = request.json.get("phone_number")
    amount = request.json.get("amount")
    response = send_stk_push(phone_number, amount)
    
    if response.get("ResponseCode") == "0":
        return {"ResponseCode": "0", "message": "Payment request sent. Check your phone."}
    else:
        return {"ResponseCode": "1", "errorMessage": "Payment request failed."}


@app.route("/send_email", methods=["GET", "POST"])
def send_mail():
    if request.method == 'POST':
        recipient_email = request.form['recipient_email']
        subject = request.form['subject']
        body = request.form['body']
        
        # Call send_email function
        status = send_email(recipient_email, subject, body)
        return render_template('send_email_result.html', status=status)
    
    return render_template('send_mail.html')

@app.route("/payment_success")
def payment_success():
    return render_template("payment_success.html")

@app.route("/payment_failure")
def payment_failure():
    return render_template("payment_failure.html")



@app.route('/view_vaccination_reminders', methods=['GET'])
@login_required
def view_vaccination_reminders():
    connection = pymysql.connect(
        host='localhost',
        user='root',
        password='',
        database='pet_health_2',
        cursorclass=pymysql.cursors.DictCursor
    )

    with connection.cursor() as cursor:
        if current_user.role == 'petowner':
            # Pet owners see only their pets' reminders
            cursor.execute("""
                SELECT vr.id, vr.pet_id, vr.vaccine_type, vr.reminder_datetime, p.name AS pet_name
                FROM vaccination_reminders vr
                JOIN pets p ON vr.pet_id = p.id
                WHERE p.owner_id = %s
            """, (current_user.id,))
        else:
            # Vets see all vaccination reminders
            cursor.execute("""
                SELECT vr.id, vr.pet_id, vr.vaccine_type, vr.reminder_datetime, 
                       p.name AS pet_name, u.username AS petowner_name
                FROM vaccination_reminders vr
                JOIN pets p ON vr.pet_id = p.id
                JOIN users u ON p.owner_id = u.id
            """)
        
        reminders = cursor.fetchall()

    connection.close()
    return render_template('view_vaccination_reminders.html', reminders=reminders, role=current_user.role)

@app.route('/view_pets')
def view_pets():
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, name FROM pets")
        pets = cursor.fetchall()
    
    return render_template("view_pets.html", pets=pets)



@app.route('/get_pet_details/<int:pet_id>')
def get_pet_details(pet_id):
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT name, species, breed, age_years, age_months, owner_id
                FROM pets WHERE id = %s
            """, (pet_id,))
            pet = cursor.fetchone()

        print("Fetched pet:", pet)  # ✅ Debugging print

        if pet:
            return jsonify({
                "name": pet[0],
                "species": pet[1],
                "breed": pet[2],
                "age": f"{pet[3]} years, {pet[4]} months",
                "owner_id": pet[5]
            })
        else:
            return jsonify({"error": "Pet not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/view_visit')
def view_visit():
    connection = pymysql.connect(
        host='localhost',
        user='root',
        password='',
        database='pet_health_2',
        cursorclass=pymysql.cursors.DictCursor
    )

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                p.id AS pet_id, 
                p.name AS pet_name, 
                u.username AS pet_owner,
                COUNT(CASE WHEN a.appointment_date < CURDATE() THEN a.id END) AS visit_count,
                COUNT(CASE WHEN a.appointment_date >= CURDATE() THEN a.id END) AS pending_appointments
            FROM pets p
            JOIN users u ON p.owner_id = u.id
            LEFT JOIN appointments a ON p.id = a.pet_id
            GROUP BY p.id, p.name, u.username
        """)
        visits = cursor.fetchall()

    connection.close()
    return render_template('view_visit.html', visits=visits)

@app.route('/view_petowners')
def view_petowners():
    connection = pymysql.connect(
        host='localhost',
        user='root',
        password='',
        database='pet_health_2',
        cursorclass=pymysql.cursors.DictCursor
    )  # Ensure you establish a connection

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT u.id, u.username, u.email, p.id AS pet_id, p.name AS pet_name, p.breed
            FROM users u
            LEFT JOIN pets p ON u.id = p.owner_id
            WHERE u.role = 'petowner'
            ORDER BY u.username
        """)
        data = cursor.fetchall()

    connection.close()  # Close connection after fetching data

    # Organizing data
    petowners = {}
    for row in data:
        owner_id = row['id']
        if owner_id not in petowners:
            petowners[owner_id] = {
                'username': row['username'],
                'email': row['email'],
                'pets': []
                
            }
        if row['pet_id']:
            petowners[owner_id]['pets'].append({
                'name': row['pet_name'],
                'breed': row['breed']
            })

    return render_template('view_petowners.html', petowners=petowners.values())


@app.route('/emergency_contact')
def emergency_contact():
    return render_template('emergency_contact.html')

@app.route('/admin/user/add', methods=['GET', 'POST'])
@login_required
def add_user():
    if session.get('user_role') != 'admin':
        flash("Access denied! Admins only.", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        try:
            # Insert the new user into the database
            with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s)", 
                               (username, email, password, role))
                connection.commit()
            flash("User added successfully!", "success")
            return redirect(url_for('manage_users'))
        except pymysql.MySQLError as e:
            flash(f"Error: {e.args[1]}", "danger")
            return redirect(url_for('manage_users'))
    
    return render_template('add_user.html')

@app.route('/admin/user/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if session.get('user_role') != 'admin':
        flash("Access denied! Admins only.", "danger")
        return redirect(url_for('login'))

    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            # Fetch the user details based on user_id
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()

            if request.method == 'POST':
                username = request.form['username']
                email = request.form['email']
                role = request.form['role']

                # Update user details in the database
                cursor.execute("UPDATE users SET username = %s, email = %s, role = %s WHERE id = %s",
                               (username, email, role, user_id))
                connection.commit()

                flash("User updated successfully!", "success")
                return redirect(url_for('manage_users'))  # Redirect to manage users page

    except pymysql.MySQLError as e:
        flash(f"Error: {e.args[1]}", "danger")

    return render_template('edit_user.html', user=user)
@app.route('/admin/pet/add', methods=['GET', 'POST'])
@login_required
def add_pet():
    # Check if the user is an admin
    if session.get('user_role') != 'admin':
        flash("Access denied! Admins only.", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Get data from the form
        name = request.form['name']
        species = request.form['species']
        breed = request.form['breed']
        age_years = request.form['age_years']
        age_months = request.form['age_months']
        photo = request.files['photo']

        # Logic to save the pet details (including photo)
        # Make sure you handle saving the photo and pet info in the database

        # Flash success message
        flash("Pet added successfully!", "success")
        return redirect(url_for('manage_pets'))  # Redirect to manage pets page

    return render_template('add_pet.html')  # Render the add pet form template

@app.route('/admin/pet/edit/<int:pet_id>', methods=['GET', 'POST'])
@login_required
def edit_pet(pet_id):
    # Check if the user is an admin
    if session.get('user_role') != 'admin':
        flash("Access denied! Admins only.", "danger")
        return redirect(url_for('login'))

    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            # Fetch pet details by ID
            cursor.execute("SELECT * FROM pets WHERE id = %s", (pet_id,))
            pet = cursor.fetchone()

            if pet is None:
                flash("Pet not found.", "danger")
                return redirect(url_for('manage_pets'))

            if request.method == 'POST':
                # Get form data and update pet details
                name = request.form['name']
                species = request.form['species']
                breed = request.form['breed']
                age_years = request.form['age_years']
                age_months = request.form['age_months']
                photo = request.files['photo'] if 'photo' in request.files else pet['photo']

                # Update pet in the database
                cursor.execute("""
                    UPDATE pets SET name = %s, species = %s, breed = %s,
                    age_years = %s, age_months = %s, photo = %s
                    WHERE id = %s
                """, (name, species, breed, age_years, age_months, photo, pet_id))
                connection.commit()

                flash("Pet updated successfully!", "success")
                return redirect(url_for('manage_pets'))

    except pymysql.MySQLError as e:
        flash(f"Database error: {e.args[1]}", "danger")

    return render_template('edit_pet.html', pet=pet)

@app.route('/admin/appointment/add', methods=['GET', 'POST'])
@login_required
def add_appointment():
    # Check if the user is an admin
    if session.get('user_role') != 'admin':
        flash("Access denied! Admins only.", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Get form data and add the appointment
        pet_id = request.form['pet_id']
        vet_id = request.form['vet_id']
        appointment_date = request.form['appointment_date']

        try:
            with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("""
                    INSERT INTO appointments (pet_id, vet_id, appointment_date)
                    VALUES (%s, %s, %s)
                """, (pet_id, vet_id, appointment_date))
                connection.commit()

            flash("Appointment added successfully!", "success")
            return redirect(url_for('manage_appointments'))

        except pymysql.MySQLError as e:
            flash(f"Database error: {e.args[1]}", "danger")
            return redirect(url_for('manage_appointments'))

    return render_template('add_appointment.html')

@app.route('/admin/appointment/edit/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
def edit_appointment(appointment_id):
    # Check if the user is an admin
    if session.get('user_role') != 'admin':
        flash("Access denied! Admins only.", "danger")
        return redirect(url_for('login'))

    try:
        # Fetch appointment data based on the appointment_id
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT * FROM appointments WHERE id = %s", (appointment_id,))
            appointment = cursor.fetchone()

            if request.method == 'POST':
                # Get updated form data
                pet_id = request.form['pet_id']
                vet_id = request.form['vet_id']
                appointment_date = request.form['appointment_date']

                cursor.execute("""
                    UPDATE appointments
                    SET pet_id = %s, vet_id = %s, appointment_date = %s
                    WHERE id = %s
                """, (pet_id, vet_id, appointment_date, appointment_id))
                connection.commit()

                flash("Appointment updated successfully!", "success")
                return redirect(url_for('manage_appointments'))

        return render_template('edit_appointment.html', appointment=appointment)

    except pymysql.MySQLError as e:
        flash(f"Database error: {e.args[1]}", "danger")
        return redirect(url_for('manage_appointments'))

@app.route('/add_health_record', methods=['GET', 'POST'])
def add_health_record():
    form = HealthRecordForm()
    

    # Fetch pet names from the database
    try:
        connection = pymysql.connect(host='localhost',
                                      user='root',
                                      password='',
                                      database='pet_health_2', 
                                      cursorclass=pymysql.cursors.DictCursor)
        cursor = connection.cursor()
        
        # Query to fetch all pet names
        cursor.execute("SELECT pet_name FROM pets")  # Assuming you have a pets table with pet_name column
        pet_names = [pet['pet_name'] for pet in cursor.fetchall()]  # Extract pet names
        
        # Pass pet names to the form as choices for the pet_name field
        form.pet_name.choices = [(name, name) for name in pet_names]

    except Exception as e:
        flash(f"Error fetching pet names: {e}", 'danger')
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

    if form.validate_on_submit():
        pet_name = form.pet_name.data
        weight = form.weight.data
        temperature = form.temperature.data
        diagnosis = form.diagnosis.data
        treatment = form.treatment.data
        comments = form.comments.data

        connection = None  # Initialize connection variable
        cursor = None  # Initialize cursor variable
        try:
            # Connect to the database
            connection = pymysql.connect(host='localhost',
                                          user='root',
                                          password='',
                                          database='pet_health_2', 
                                          cursorclass=pymysql.cursors.DictCursor)
            cursor = connection.cursor()
            
            # Insert health record into the database
            query = """
                INSERT INTO health_records (pet_name, weight, temperature, diagnosis, treatment, comments)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (pet_name, weight, temperature, diagnosis, treatment, comments))
            connection.commit()
            flash('Health record added successfully!', 'success')
        except Exception as e:
            if connection:
                connection.rollback()  # Rollback only if connection is created
            flash(f'Error adding health record: {e}', 'danger')
        finally:
            # Close cursor and connection only if they were created
            if cursor is not None:
                cursor.close()
            if connection is not None:
                connection.close()

        return redirect(url_for('view_health_records'))

    return render_template('add_health_record.html', form=form)


@app.route('/manage_health_records')
@login_required
def manage_health_records():
    # Fetch health records (since pet_name is already stored directly)
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, pet_name, weight, temperature, diagnosis, treatment, comments, created_at
            FROM health_records
            ORDER BY created_at DESC
        """)
        health_records = cursor.fetchall()

    return render_template('manage_health_records.html', health_records=health_records)


@app.route('/edit_health_record/<int:record_id>', methods=['GET', 'POST'])
@login_required
def edit_health_record(record_id):
    if request.method == 'POST':
        weight = request.form['weight']
        temperature = request.form['temperature']
        diagnosis = request.form['diagnosis']
        treatment = request.form['treatment']
        comments = request.form['comments']

        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE health_records
                SET weight=%s, temperature=%s, diagnosis=%s, treatment=%s, comments=%s
                WHERE id=%s
            """, (weight, temperature, diagnosis, treatment, comments, record_id))
            connection.commit()

        return redirect(url_for('manage_health_records'))  # ✅ after editing, redirect back

    # Fetch the health record to edit
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM health_records WHERE id = %s", (record_id,))
        health_record = cursor.fetchone()

    if not health_record:
        return "Health record not found.", 404  # If not found, show 404

    return render_template('edit_health_record.html', health_record=health_record)  # ✅ render form


@app.route('/delete_health_record/<int:record_id>', methods=['POST', 'GET'])
@login_required
def delete_health_record(record_id):
    # logic for deleting
    pass

@app.route('/manage_appointments')
@login_required
def manage_appointments():
    # Fetch all appointments for the admin dashboard
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("""
                SELECT appointments.*, pets.name AS pet_name, users.username AS vet_name
                FROM appointments
                JOIN pets ON appointments.pet_id = pets.id
                JOIN users ON appointments.vet_id = users.id
                ORDER BY appointments.appointment_date ASC
            """)
            appointments = cursor.fetchall()

        return render_template('manage_appointments.html', appointments=appointments)

    except pymysql.MySQLError as e:
        flash(f"Database error: {e.args[1]}", "danger")
        return redirect(url_for('manage_appointments'))


@app.route('/admin/manage_pets')
@login_required
def manage_pets_admin():
    cursor = connection.cursor()
    cursor.execute("SELECT pets.*, users.username FROM pets JOIN users ON pets.owner_id = users.id")
    pets = cursor.fetchall()
    cursor.close()

    return render_template('manage_pets_admin.html', pets=pets)


def get_db_connection():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='',
        db='pet_health_2',  # Change if needed
        cursorclass=pymysql.cursors.DictCursor
    )

@app.route('/admin/add_pet', methods=['GET', 'POST'])
@login_required
def add_pet_admin():
    if request.method == 'POST':
        name = request.form['name']
        species = request.form['species']
        breed = request.form['breed']
        age_years = request.form['age_years']
        age_months = request.form['age_months']
        registration_date = request.form['registration_date']
        owner_id = current_user.id  # Assuming the current_user is the logged-in admin

        # Handle photo upload (if any)
        photo = request.files['photo']
        photo_path = None
        if photo:
            filename = secure_filename(photo.filename)
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(photo_path)

        # Insert pet data into the database
        cursor = connection.cursor()
        cursor.execute(
            """INSERT INTO pets (name, species, breed, age_years, age_months, registration_date, photo, owner_id) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (name, species, breed, age_years, age_months, registration_date, photo_path, owner_id)
        )
        connection.commit()
        cursor.close()

        flash('Pet added successfully!', 'success')
        return redirect(url_for('manage_pets_admin'))

    return render_template('add_pet_admin.html')

@app.route('/admin/edit_appointment/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
def edit_appointment_admin(appointment_id):
    # Logic for editing the appointment
    if request.method == 'POST':
        # Update the appointment based on form data
        new_date = request.form['appointment_date']
        new_reason = request.form['reason']

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE appointments
                    SET appointment_date = %s, reason = %s
                    WHERE id = %s
                """, (new_date, new_reason, appointment_id))
                connection.commit()

            flash("Appointment updated successfully!", "success")
            return redirect(url_for('manage_appointments'))

        except pymysql.MySQLError as e:
            flash(f"Database error: {e.args[1]}", "danger")
            return redirect(url_for('manage_appointments'))

    # Fetch the current details of the appointment for editing
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT * FROM appointments WHERE id = %s
        """, (appointment_id,))
        appointment = cursor.fetchone()

    return render_template('edit_appointment_admin.html', appointment=appointment)

@app.route('/admin/delete_appointment/<int:appointment_id>', methods=['GET'])
@login_required
def delete_appointment_admin(appointment_id):
    # Logic for deleting the appointment
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                DELETE FROM appointments WHERE id = %s
            """, (appointment_id,))
            connection.commit()

        flash("Appointment deleted successfully!", "success")
        return redirect(url_for('manage_appointments'))

    except pymysql.MySQLError as e:
        flash(f"Database error: {e.args[1]}", "danger")
        return redirect(url_for('manage_appointments'))



@app.route('/delete_vaccination_reminder/<int:reminder_id>')
def delete_vaccination_reminder(reminder_id):
    connection = pymysql.connect(
        host='localhost',
        user='your_db_user',
        password='your_db_password',
        database='pet_health_2'
    )

    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM vaccination_reminders WHERE id = %s", (reminder_id,))
            connection.commit()

    finally:
        connection.close()

    return redirect(url_for('manage_vaccination_reminders'))

@app.route('/edit_vaccination_reminder/<int:reminder_id>', methods=['GET', 'POST'])
def edit_vaccination_reminder(reminder_id):
    # Establish connection to the database
    connection = pymysql.connect(
        host='localhost',
        user='root',
        password='',
        database='pet_health_2'
    )

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM vaccination_reminders WHERE id = %s", (reminder_id,))
            reminder = cursor.fetchone()

            # If reminder is found, map the tuple to a dictionary
            if reminder:
                reminder_dict = {
                    'id': reminder[0],
                    'pet_id': reminder[1],
                    'vaccine_type': reminder[2],
                    'reminder_datetime': reminder[3],
                    'created_at': reminder[4]
                }

                if request.method == 'POST':
                    # Handle the form submission for editing
                    vaccine_type = request.form['vaccine_type']
                    reminder_datetime = request.form['reminder_datetime']

                    cursor.execute("""
                        UPDATE vaccination_reminders
                        SET vaccine_type = %s, reminder_datetime = %s
                        WHERE id = %s
                    """, (vaccine_type, reminder_datetime, reminder_id))
                    connection.commit()

                    return redirect(url_for('manage_vaccination_reminders'))

                return render_template('edit_vaccination_reminder.html', reminder=reminder_dict)

            else:
                return "Reminder not found", 404

    finally:
        connection.close()




from flask import send_file
import pymysql
import pandas as pd
import matplotlib.pyplot as plt
import zipfile
import os
from io import BytesIO

@app.route('/generate_all_reports')
def generate_all_reports():
    # Connect to the database
    connection = pymysql.connect(
        host='localhost',
        user='root',
        password='',
        database='pet_health_2'
    )

    try:
        with connection.cursor() as cursor:
            # --- Appointments Report ---
            cursor.execute("SELECT id, pet_id, vet_id, appointment_date, reason, created_at FROM appointments")
            appointments_data = cursor.fetchall()

            cursor.execute("SELECT reason, COUNT(*) FROM appointments GROUP BY reason")
            appointment_reasons = cursor.fetchall()

            appointment_reasons_labels = [item[0] for item in appointment_reasons]
            appointment_counts = [item[1] for item in appointment_reasons]

            fig, ax = plt.subplots(figsize=(8, 6))
            ax.bar(appointment_reasons_labels, appointment_counts, color='#28a745')
            ax.set_xlabel('Reason', fontsize=14, fontweight='bold')
            ax.set_ylabel('Appointments Count', fontsize=14, fontweight='bold')
            ax.set_title('Appointments by Reason', fontsize=16, fontweight='bold', color='#28a745')
            ax.grid(True, axis='y', linestyle='--', alpha=0.6)
            plt.xticks(rotation=45, ha='right', fontsize=12)
            img_io_appointments = BytesIO()
            fig.tight_layout()
            fig.savefig(img_io_appointments, format='png')
            img_io_appointments.seek(0)

            df_appointments = pd.DataFrame(appointments_data, columns=['ID', 'Pet ID', 'Vet ID', 'Appointment Date', 'Reason', 'Date Created'])
            csv_path_appointments = os.path.join('static', 'appointments_report.csv')
            df_appointments.to_csv(csv_path_appointments, index=False)

            # --- Pets Report ---
            cursor.execute("SELECT id, name, species, breed, registration_date, age_years, age_months, photo, owner_id, created_at FROM pets")
            pets_data = cursor.fetchall()

            cursor.execute("SELECT breed, COUNT(*) FROM pets GROUP BY breed")
            pet_breeds = cursor.fetchall()

            pet_breeds_labels = [item[0] for item in pet_breeds]
            pet_counts = [item[1] for item in pet_breeds]

            fig, ax = plt.subplots(figsize=(8, 6))
            ax.bar(pet_breeds_labels, pet_counts, color='#007bff')
            ax.set_xlabel('Breed', fontsize=14, fontweight='bold')
            ax.set_ylabel('Pets Count', fontsize=14, fontweight='bold')
            ax.set_title('Pets by Breed', fontsize=16, fontweight='bold', color='#007bff')
            ax.grid(True, axis='y', linestyle='--', alpha=0.6)
            plt.xticks(rotation=45, ha='right', fontsize=12)
            img_io_pets = BytesIO()
            fig.tight_layout()
            fig.savefig(img_io_pets, format='png')
            img_io_pets.seek(0)

            df_pets = pd.DataFrame(pets_data, columns=['ID', 'Name', 'Species', 'Breed', 'Registration Date', 'Age (Years)', 'Age (Months)', 'Photo', 'Owner ID', 'Date Created'])
            csv_path_pets = os.path.join('static', 'pets_report.csv')
            df_pets.to_csv(csv_path_pets, index=False)

            # --- Vaccination Reminders Report ---
            cursor.execute("SELECT id, pet_id, vaccine_type, reminder_datetime FROM vaccination_reminders")
            reminders_data = cursor.fetchall()

            cursor.execute("SELECT vaccine_type, COUNT(*) FROM vaccination_reminders GROUP BY vaccine_type")
            reminder_types = cursor.fetchall()

            reminder_types_labels = [item[0] for item in reminder_types]
            reminder_counts = [item[1] for item in reminder_types]

            fig, ax = plt.subplots(figsize=(8, 6))
            ax.bar(reminder_types_labels, reminder_counts, color='#ffc107')
            ax.set_xlabel('Vaccination Type', fontsize=14, fontweight='bold')
            ax.set_ylabel('Reminder Count', fontsize=14, fontweight='bold')
            ax.set_title('Vaccination Reminders by Type', fontsize=16, fontweight='bold', color='#ffc107')
            ax.grid(True, axis='y', linestyle='--', alpha=0.6)
            plt.xticks(rotation=45, ha='right', fontsize=12)
            img_io_reminders = BytesIO()
            fig.tight_layout()
            fig.savefig(img_io_reminders, format='png')
            img_io_reminders.seek(0)

            df_reminders = pd.DataFrame(reminders_data, columns=['ID', 'Pet ID', 'Vaccination Type', 'Reminder Date'])
            csv_path_reminders = os.path.join('static', 'vaccination_reminders_report.csv')
            df_reminders.to_csv(csv_path_reminders, index=False)

            # --- Health Records Report ---
            cursor.execute("SELECT id, pet_name, weight, temperature,  diagnosis, treatment, comments, created_at FROM health_records")
            health_records_data = cursor.fetchall()

            cursor.execute("SELECT diagnosis, COUNT(*) FROM health_records GROUP BY diagnosis")
            health_diagnosis = cursor.fetchall()

            health_diagnosis_labels = [item[0] for item in health_diagnosis]
            health_counts = [item[1] for item in health_diagnosis]

            fig, ax = plt.subplots(figsize=(8, 6))
            ax.bar(health_diagnosis_labels, health_counts, color='#dc3545')
            ax.set_xlabel('Diagnosis', fontsize=14, fontweight='bold')
            ax.set_ylabel('Records Count', fontsize=14, fontweight='bold')
            ax.set_title('Health Records by Diagnosis', fontsize=16, fontweight='bold', color='#dc3545')
            ax.grid(True, axis='y', linestyle='--', alpha=0.6)
            plt.xticks(rotation=45, ha='right', fontsize=12)
            img_io_health = BytesIO()
            fig.tight_layout()
            fig.savefig(img_io_health, format='png')
            img_io_health.seek(0)

            df_health = pd.DataFrame(health_records_data, columns=['ID', 'Pet ID', 'Vet ID', 'Visit Date', 'Diagnosis', 'Treatment', 'Notes', 'Date Created'])
            csv_path_health = os.path.join('static', 'health_records_report.csv')
            df_health.to_csv(csv_path_health, index=False)

            # --- Users Report ---
            cursor.execute("SELECT id, username, email, role, created_at FROM users")
            users_data = cursor.fetchall()

            cursor.execute("SELECT role, COUNT(*) FROM users GROUP BY role")
            user_roles = cursor.fetchall()

            user_roles_labels = [item[0] for item in user_roles]
            user_counts = [item[1] for item in user_roles]

            fig, ax = plt.subplots(figsize=(8, 6))
            ax.bar(user_roles_labels, user_counts, color='#6f42c1')
            ax.set_xlabel('Role', fontsize=14, fontweight='bold')
            ax.set_ylabel('User Count', fontsize=14, fontweight='bold')
            ax.set_title('Users by Role', fontsize=16, fontweight='bold', color='#6f42c1')
            ax.grid(True, axis='y', linestyle='--', alpha=0.6)
            plt.xticks(rotation=45, ha='right', fontsize=12)
            img_io_users = BytesIO()
            fig.tight_layout()
            fig.savefig(img_io_users, format='png')
            img_io_users.seek(0)

            df_users = pd.DataFrame(users_data, columns=['ID', 'Username', 'Email', 'Role', 'Date Created'])
            csv_path_users = os.path.join('static', 'users_report.csv')
            df_users.to_csv(csv_path_users, index=False)

            # --- Create Zip Bundle ---
            zip_io = BytesIO()
            with zipfile.ZipFile(zip_io, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Appointments
                zipf.writestr('appointments_report.png', img_io_appointments.getvalue())
                with open(csv_path_appointments, 'rb') as f:
                    zipf.writestr('appointments_report.csv', f.read())

                # Pets
                zipf.writestr('pets_report.png', img_io_pets.getvalue())
                with open(csv_path_pets, 'rb') as f:
                    zipf.writestr('pets_report.csv', f.read())

                # Vaccination Reminders
                zipf.writestr('vaccination_reminders_report.png', img_io_reminders.getvalue())
                with open(csv_path_reminders, 'rb') as f:
                    zipf.writestr('vaccination_reminders_report.csv', f.read())

                # Health Records
                zipf.writestr('health_records_report.png', img_io_health.getvalue())
                with open(csv_path_health, 'rb') as f:
                    zipf.writestr('health_records_report.csv', f.read())

                # Users
                zipf.writestr('users_report.png', img_io_users.getvalue())
                with open(csv_path_users, 'rb') as f:
                    zipf.writestr('users_report.csv', f.read())

            zip_io.seek(0)

            # Return the zip file for download
            return send_file(zip_io, mimetype='application/zip', as_attachment=True, download_name="all_reports.zip")

    finally:
        connection.close()
        
        

@app.route('/add_vaccination_reminder', methods=['GET', 'POST'])
@login_required
def add_vaccination_reminder():
    # Fetch the list of pets for the dropdown
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, name FROM pets")
        pets = cursor.fetchall()

    if request.method == 'POST':
        pet_id = request.form['pet_id']
        vaccine_type = request.form['vaccine_type']
        reminder_datetime = request.form['reminder_datetime']

        # Convert the reminder_datetime string to a proper datetime object
        reminder_datetime = datetime.strptime(reminder_datetime, "%Y-%m-%dT%H:%M")

        # Insert the reminder into the database
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO vaccination_reminders (pet_id, vaccine_type, reminder_datetime) 
                   VALUES (%s, %s, %s)""",
                (pet_id, vaccine_type, reminder_datetime)
            )
            connection.commit()

        flash('Vaccination reminder added successfully!', 'success')
        return redirect(url_for('manage_vaccination_reminders'))

    return render_template('add_vaccination_reminder.html', pets=pets)


@app.route('/manage_vaccination_reminders')
def manage_vaccination_reminders():
    # Create a connection to the database
    connection = pymysql.connect(
        host='localhost',
        user='root',
        password='',
        database='pet_health_2',
        cursorclass=pymysql.cursors.DictCursor  # Use DictCursor to fetch rows as dictionaries
    )
    
    try:
        with connection.cursor() as cursor:
            # Query to get all vaccination reminders
            query = "SELECT id, pet_id, vaccine_type, reminder_datetime, created_at FROM vaccination_reminders"
            cursor.execute(query)
            reminders = cursor.fetchall()  # Fetch all records as dictionaries
            
        # Pass the reminders to the template
        return render_template('manage_vaccination_reminders.html', reminders=reminders)
    finally:
        connection.close()

@app.route('/admin/edit_pet/<int:pet_id>', methods=['GET', 'POST'])
def edit_pet_admin(pet_id):
    # Connect to database (update password if needed)
    conn = pymysql.connect(
        host='localhost',
        user='root',
        password='',  # <--- leave empty if your MySQL root has no password
        database='pet_health_2'
    )
    cursor = conn.cursor()

    # Retrieve the pet data based on pet_id
    cursor.execute("SELECT * FROM pets WHERE id = %s", (pet_id,))
    pet = cursor.fetchone()

    if pet:
        if request.method == 'POST':
            name = request.form['name']
            species = request.form['species']
            breed = request.form['breed']
            age_years = request.form['age_years']
            age_months = request.form['age_months']
            registration_date = request.form['registration_date']

            # Update the pet record
            cursor.execute("""
                UPDATE pets 
                SET name = %s, species = %s, breed = %s, age_years = %s, age_months = %s, registration_date = %s
                WHERE id = %s
            """, (name, species, breed, age_years, age_months, registration_date, pet_id))
            conn.commit()

            # Redirect after successful update
            return redirect(url_for('manage_pets_admin'))
    
    cursor.close()
    conn.close()

    return render_template('edit_pet_admin.html', pet=pet)


@app.route('/admin/delete_pet/<int:pet_id>', methods=['GET'])
def delete_pet_admin(pet_id):
    # Your logic to delete the pet
    conn = pymysql.connect(host='localhost', user='root', password='password', database='pet_health_2')
    cursor = conn.cursor()

    # Delete the pet data based on pet_id
    cursor.execute("DELETE FROM pets WHERE id = %s", (pet_id,))
    conn.commit()

    cursor.close()
    conn.close()

    # Redirect to the manage pets page after deletion
    return redirect(url_for('manage_pets_admin'))

# Run the app
if __name__ == "__main__":
    app.run(debug=True)
