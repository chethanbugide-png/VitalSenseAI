import sqlite3
import os
import json
from werkzeug.security import generate_password_hash
DB_PATH = 'vitalsense.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create Patients Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            weight REAL NOT NULL,
            history_hypertension INTEGER,
            history_diabetes INTEGER,
            history_heart_disease INTEGER,
            room_no TEXT,
            bed_no TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    
    # Create Assessments Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_db_id INTEGER NOT NULL,
            heart_rate REAL,
            sys_bp REAL,
            dia_bp REAL,
            spo2 REAL,
            temperature REAL,
            resp_rate REAL,
            chest_pain INTEGER,
            shortness_breath INTEGER,
            fever INTEGER,
            dizziness INTEGER,
            fatigue INTEGER,
            palpitations INTEGER,
            nausea INTEGER,
            headache INTEGER,
            
            ai_risk_level INTEGER,
            ai_confidence REAL,
            recommended_doctor TEXT,
            recommended_actions TEXT,
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_db_id) REFERENCES patients(id)
        )
    ''')
    
    # Create Prescriptions Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prescriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_db_id INTEGER NOT NULL UNIQUE,
            prescription_text TEXT,
            instructions_text TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_db_id) REFERENCES patients(id),
            FOREIGN KEY(created_by) REFERENCES users(id)
        )
    ''')
    
    # Insert default users if none exist
    cursor.execute('SELECT COUNT(*) as count FROM users')
    if cursor.fetchone()['count'] == 0:
        cursor.execute('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)', 
                       ('doctor1', generate_password_hash('password'), 'doctor'))
        cursor.execute('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)', 
                       ('nurse1', generate_password_hash('password'), 'nurse'))
                       
    conn.commit()
    conn.close()

def add_patient(patient_id, name, age, gender, weight, hist_hyper, hist_diab, hist_heart, room_no=None, bed_no=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO patients (patient_id, name, age, gender, weight, 
                                  history_hypertension, history_diabetes, history_heart_disease, room_no, bed_no)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (patient_id, name, age, gender, weight, hist_hyper, hist_diab, hist_heart, room_no, bed_no))
        patient_db_id = cursor.lastrowid
        conn.commit()
    except sqlite3.IntegrityError:
        # If patient exists, return their id
        cursor.execute('SELECT id FROM patients WHERE patient_id = ?', (patient_id,))
        patient_db_id = cursor.fetchone()['id']
    finally:
        conn.close()
    return patient_db_id

def get_patient(patient_id):
    conn = get_db_connection()
    patient = conn.execute('SELECT * FROM patients WHERE patient_id = ?', (patient_id,)).fetchone()
    conn.close()
    return dict(patient) if patient else None

def get_patient_by_name(name):
    conn = get_db_connection()
    # Case-insensitive search
    patient = conn.execute('SELECT * FROM patients WHERE LOWER(name) = LOWER(?)', (name,)).fetchone()
    conn.close()
    return dict(patient) if patient else None

def add_assessment(patient_db_id, data_dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO assessments (
            patient_db_id, heart_rate, sys_bp, dia_bp, spo2, temperature, resp_rate,
            chest_pain, shortness_breath, fever, dizziness, fatigue, palpitations, nausea, headache,
            ai_risk_level, ai_confidence, recommended_doctor, recommended_actions
        ) VALUES (
            :patient_db_id, :heart_rate, :sys_bp, :dia_bp, :spo2, :temperature, :resp_rate,
            :chest_pain, :shortness_breath, :fever, :dizziness, :fatigue, :palpitations, :nausea, :headache,
            :ai_risk_level, :ai_confidence, :recommended_doctor, :recommended_actions
        )
    ''', {**data_dict, 'patient_db_id': patient_db_id})
    
    assessment_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return assessment_id

def get_patient_history(patient_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get patient db id
    patient = cursor.execute('SELECT id, name FROM patients WHERE patient_id = ?', (patient_id,)).fetchone()
    if not patient:
        conn.close()
        return None, []
        
    patient_db_id = patient['id']
    patient_name = patient['name']
    
    assessments = cursor.execute('''
        SELECT * FROM assessments 
        WHERE patient_db_id = ? 
        ORDER BY created_at DESC
    ''', (patient_db_id,)).fetchall()
    
    conn.close()
    return patient_name, [dict(row) for row in assessments]

def get_all_patients_with_latest_assessment():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Fetch patients and their most recent assessment
    query = '''
        SELECT p.patient_id, p.name, p.age, p.gender, p.room_no, p.bed_no,
               a.ai_risk_level, a.created_at as last_assessment_date
        FROM patients p
        LEFT JOIN assessments a ON p.id = a.patient_db_id
        WHERE a.id = (
            SELECT id FROM assessments 
            WHERE patient_db_id = p.id 
            ORDER BY created_at DESC LIMIT 1
        )
        ORDER BY a.created_at DESC
    '''
    rows = cursor.execute(query).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_user_by_username(username):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return dict(user) if user else None

def update_patient(patient_id, name, age, gender, weight, hist_hyper, hist_diab, hist_heart, room_no, bed_no):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE patients
        SET name = ?, age = ?, gender = ?, weight = ?,
            history_hypertension = ?, history_diabetes = ?, history_heart_disease = ?,
            room_no = ?, bed_no = ?
        WHERE patient_id = ?
    ''', (name, age, gender, weight, hist_hyper, hist_diab, hist_heart, room_no, bed_no, patient_id))
    conn.commit()
    conn.close()

# Initialize db if it doesn't exist
if not os.path.exists(DB_PATH):
    init_db()

def get_prescription_by_patient_db_id(patient_db_id):
    conn = get_db_connection()
    prescription = conn.execute('SELECT * FROM prescriptions WHERE patient_db_id = ?', (patient_db_id,)).fetchone()
    conn.close()
    return dict(prescription) if prescription else None

def save_prescription(patient_db_id, prescription_text, instructions_text, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if prescription exists
    existing = cursor.execute('SELECT id FROM prescriptions WHERE patient_db_id = ?', (patient_db_id,)).fetchone()
    
    if existing:
        cursor.execute('''
            UPDATE prescriptions 
            SET prescription_text = ?, instructions_text = ?, updated_at = CURRENT_TIMESTAMP
            WHERE patient_db_id = ?
        ''', (prescription_text, instructions_text, patient_db_id))
    else:
        cursor.execute('''
            INSERT INTO prescriptions (patient_db_id, prescription_text, instructions_text, created_by)
            VALUES (?, ?, ?, ?)
        ''', (patient_db_id, prescription_text, instructions_text, user_id))
        
    conn.commit()
    conn.close()
