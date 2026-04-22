from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from ai_handler import predict_waste

app = Flask(__name__)
app.secret_key = 'intelli_bin_ultimate_pro_secure'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- DATABASE CONNECTION ---
def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn
def classify_waste(image_path):
    # In a real app, this is where a Machine Learning model (like TensorFlow) lives.
    # For now, we will simulate it by picking a category based on common waste types.
    categories = ["Plastic Waste", "Organic/Food Waste", "Electronic Waste", "Hazardous Waste"]
    import random
    return random.choice(categories)

# --- DATABASE INITIALIZATION & PRE-REGISTRATION ---
def init_db():
    db = get_db()
    # 1. Users Table
    db.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE, 
        password TEXT, role TEXT, district TEXT, contact TEXT, points INTEGER DEFAULT 0)''')
    
    # 2. Complaints Table (REPLACE THIS SECTION)
    db.execute('''CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, 
        district TEXT, area TEXT, address TEXT, nearby_zone TEXT, detail_desc TEXT,
        report_date TEXT, user_image TEXT, supervisor_image TEXT, 
        supervisor_id INTEGER, status TEXT DEFAULT 'Pending',
        muni_note TEXT, 
        ai_category TEXT, 
        priority TEXT)''') # <--- WE ADDED THESE TWO FOLDERS
    
    db.commit()

    # Pre-register 5 Municipality Officials (Admin Level)
    muni_officials = [
        ('Admin 1', 'muni1@tn.gov.in', 'muni123'),
        ('Admin 2', 'muni2@tn.gov.in', 'muni456'),
        ('Admin 3', 'muni3@tn.gov.in', 'muni789'),
        ('Admin 4', 'muni4@tn.gov.in', 'muni101'),
        ('Admin 5', 'muni5@tn.gov.in', 'muni202')
    ]
    for name, email, pwd in muni_officials:
        try:
            db.execute("INSERT INTO users (name, email, password, role) VALUES (?,?,?,?)", 
                       (name, email, pwd, 'municipality'))
        except sqlite3.IntegrityError: pass

    # Pre-register Supervisors for all 38 Districts of Tamil Nadu
    tn_districts = [
        "Ariyalur", "Chengalpattu", "Chennai", "Coimbatore", "Cuddalore", "Dharmapuri", "Dindigul", "Erode", 
        "Kallakurichi", "Kanchipuram", "Kanyakumari", "Karur", "Krishnagiri", "Madurai", "Mayiladuthurai", 
        "Nagapattinam", "Namakkal", "Nilgiris", "Perambalur", "Pudukkottai", "Ramanathapuram", "Ranipet", 
        "Salem", "Sivaganga", "Tenkasi", "Thanjavur", "Theni", "Thoothukudi", "Tiruchirappalli", "Tirunelveli", 
        "Tirupathur", "Tiruppur", "Tiruvallur", "Tiruvannamalai", "Tiruvarur", "Vellore", "Viluppuram", "Virudhunagar"
    ]
    for i, dist in enumerate(tn_districts):
        contact = f"98400{str(i).zfill(5)}" # Unique ID based on district index
        email = f"sup_{dist.lower()}@clean.tn"
        try:
            db.execute("INSERT INTO users (name, email, password, role, district, contact) VALUES (?,?,?,?,?,?)", 
                       (f"Supervisor {dist}", email, "sup123", 'supervisor', dist, contact))
        except sqlite3.IntegrityError: pass
    db.commit()

# --- ROUTES ---

@app.route('/')
def index(): 
    return render_template('index.html')

@app.route('/report_waste', methods=['POST'])
def report_waste():
    # ... (your existing code to get area, district, and file) ...
    
    if file:
        # 1. Save the file first
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # 2. RUN THE AI ANALYSIS HERE
        ai_type = classify_waste(file_path) 
        
        # 3. SAVE TO DATABASE (Notice we add ai_category here)
        db = get_db()
        db.execute("""
            INSERT INTO complaints (user_id, area, district, detail_desc, user_image, ai_category, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (session['user_id'], area, district, description, filename, ai_type, 'Pending'))
        db.commit()
        
    return redirect(url_for('citizen_dash'))

@app.route('/citizen-auth')
def citizen_auth_page():
    return render_template('citizen_auth.html')

@app.route('/municipality-login')
def municipality_login_page():
    return render_template('municipality_login.html')

@app.route('/supervisor-login')
def supervisor_login_page():
    return render_template('supervisor_login.html')

# Centralized Auth for all roles
@app.route('/auth', methods=['POST'])
def auth():
    db = get_db()
    action = request.form.get('action')
    email = request.form.get('email')
    pwd = request.form.get('password')

    if action == 'register':
        try:
            db.execute("INSERT INTO users (name, email, password, role, district, contact) VALUES (?,?,?,?,?,?)", 
                       (request.form['name'], email, pwd, 'citizen', request.form['district'], request.form['contact']))
            db.commit()
            flash("Registration successful! Please login.")
        except sqlite3.IntegrityError:
            flash("Email already registered.")
            return redirect(url_for('citizen_auth_page'))
    
    user = db.execute("SELECT * FROM users WHERE email=? AND password=?", (email, pwd)).fetchone()
    if user:
        session.update({
            'user_id': user['id'], 
            'role': user['role'], 
            'name': user['name'], 
            'district': user['district']
        })
        return redirect(url_for('dashboard'))
    
    flash("Invalid email or password.")
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('index'))
    db = get_db()
    u_id, role = session['user_id'], session['role']
    
    if role == 'citizen':
        reports = db.execute("SELECT * FROM complaints WHERE user_id=? ORDER BY id DESC", (u_id,)).fetchall()
        user_data = db.execute("SELECT * FROM users WHERE id=?", (u_id,)).fetchone()
        return render_template('citizen_dash.html', reports=reports, user=user_data)
    
    elif role == 'municipality':
        # Admin sees all reports and all supervisors for assignment
        reports = db.execute("SELECT c.*, u.name as r_name FROM complaints c JOIN users u ON c.user_id = u.id").fetchall()
        supervisors = db.execute("SELECT * FROM users WHERE role='supervisor'").fetchall()
        return render_template('municipality_dash.html', reports=reports, supervisors=supervisors)
    
    elif role == 'supervisor':
        # Supervisor sees tasks specifically assigned to them by Admin
        reports = db.execute("SELECT c.*, u.name as r_name FROM complaints c JOIN users u ON c.user_id = u.id WHERE c.supervisor_id=?", (u_id,)).fetchall()
        return render_template('supervisor_dash.html', reports=reports)

@app.route('/report', methods=['POST'])
def report():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    area = request.form.get('area')
    address = request.form.get('address')
    nearby_zone = request.form.get('nearby_zone')
    detail_desc = request.form.get('detail_desc')
    district = request.form.get('district')
    file = request.files['image']

    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # --- CALL YOUR AI HANDLER HERE ---
        # It returns two values: category and priority
        ai_category, ai_priority = predict_waste(file_path)

        db = get_db()
        # Save it to the database! 
        # Make sure your INSERT statement includes ai_category
        db.execute("""
            INSERT INTO complaints 
            (user_id, area, district, address, nearby_zone, detail_desc, user_image, ai_category, priority, status) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (session['user_id'], area, district, address, nearby_zone, detail_desc, filename, ai_category, ai_priority, 'Pending'))
        
        db.commit()
        
    
    return redirect(url_for('dashboard'))
# Municipality Admin forwards task to Supervisor with an instruction note
@app.route('/assign_task/<int:id>', methods=['POST'])
def assign_task(id):
    s_id = request.form['supervisor_id']
    note = request.form.get('muni_note', 'Please clear this immediately.')
    db = get_db()
    db.execute("UPDATE complaints SET supervisor_id=?, muni_note=?, status='Assigned' WHERE id=?", 
               (s_id, note, id))
    db.commit()
    flash("Task forwarded to District Supervisor.")
    return redirect(url_for('dashboard'))

# Supervisor uploads clearance proof
@app.route('/supervisor_resolve/<int:id>', methods=['POST'])
def supervisor_resolve(id):
    file = request.files['res_image']
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        db = get_db()
        db.execute("UPDATE complaints SET supervisor_image=?, status='Cleared by Supervisor' WHERE id=?", (filename, id))
        db.commit()
        flash("Response submitted. Awaiting Municipality verification.")
    return redirect(url_for('dashboard'))

@app.route('/muni_verify/<int:id>')
def muni_verify(id):
    if 'user_id' not in session or session['role'] != 'municipality':
        return redirect(url_for('index'))
        
    db = get_db()
    # 1. Update status to 'Cleared' so it appears in Analytics
    db.execute("UPDATE complaints SET status='Cleared' WHERE id=?", (id,))
    
    # 2. Find the citizen who reported it to give them points
    comp = db.execute("SELECT user_id FROM complaints WHERE id=?", (id,)).fetchone()
    if comp:
        db.execute("UPDATE users SET points = points + 100 WHERE id=?", (comp['user_id'],))
    
    db.commit()
    flash("Report Verified! Moved to Analytics.")
    return redirect(url_for('dashboard'))

# Final Step: Admin verifies and citizen gets points

@app.route('/municipality/analytics')
def muni_analytics():
    db = get_db()
    # ONLY status='Cleared' will show up here
    resolved = db.execute("""
        SELECT c.*, u.name as citizen_name, s.name as supervisor_name 
        FROM complaints c 
        JOIN users u ON c.user_id = u.id 
        LEFT JOIN users s ON c.supervisor_id = s.id
        WHERE c.status = 'Cleared' 
        ORDER BY c.id DESC
    """).fetchall()
    return render_template('muni_analytics.html', reports=resolved)
   

@app.route('/logout')
def logout(): 
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)