from flask import Flask, render_template, request, jsonify, make_response, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from functools import wraps
import joblib
import pandas as pd
import numpy as np
import io
import os
import uuid
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import database

app = Flask(__name__)
app.secret_key = os.urandom(24)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json: return jsonify({'error': 'Unauthorized'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def roles_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                if request.is_json: return jsonify({'error': 'Unauthorized'}), 401
                return redirect(url_for('login'))
            if session.get('role') not in roles:
                if request.is_json: return jsonify({'error': 'Forbidden'}), 403
                flash('You do not have permission to access that page.', 'error')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.context_processor
def inject_user():
    return dict(current_user={'username': session.get('username'), 'role': session.get('role')} if 'user_id' in session else None)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = database.get_user_by_username(username)
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('history'))
        else:
            flash('Invalid username or password', 'error')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Load Model At Application Startup
# Note: we wrap in try-except so the app can start before model is trained
try:
    model = joblib.load('models/model.pkl')
    scaler = joblib.load('models/scaler.pkl')
    feature_cols = joblib.load('models/feature_cols.pkl')
    print("AI Model loaded successfully.")
except FileNotFoundError:
    print("Warning: Model files not found. Please run ml/train_model.py first.")
    model, scaler, feature_cols = None, None, None

def determine_recommendations(risk_level, data):
    # Rule-based recommendations based on AI finding and vitals
    actions = []
    doctor = "General Physician"
    
    if risk_level == 0:
        actions.append("Routine observation.")
        actions.append("Advise patient on healthy lifestyle habits.")
    elif risk_level == 1:
        actions.append("Requires close monitoring of vital signs.")
        actions.append("Consider further diagnostic tests.")
        if float(data.get('sys_bp', 0)) > 140 or float(data.get('heart_rate', 0)) > 100 or int(data.get('palpitations', 0)):
            doctor = "Cardiologist"
        elif int(data.get('shortness_breath', 0)):
            doctor = "Pulmonologist"
    elif risk_level == 2:
        actions.append("IMMEDIATE MEDICAL INTERVENTION REQUIRED.")
        actions.append("Transfer to ICU/Emergency Department.")
        doctor = "Emergency Specialist"
        if int(data.get('chest_pain', 0)):
            doctor = "Cardiologist (Urgent)"
            actions.append("Administer Oxygen and prepare ECG.")
        elif float(data.get('spo2', 100)) < 90:
            doctor = "Pulmonologist / Critical Care"
            actions.append("Start Oxygen Therapy immediately.")
        
    return doctor, ", ".join(actions)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/assessment')
@roles_required('nurse')
def assessment():
    return render_template('assessment.html')

@app.route('/predict', methods=['POST'])
@roles_required('nurse')
def predict():
    if not model or not scaler or not feature_cols:
        return jsonify({'error': 'AI Model is not trained yet!'}), 500
        
    data = request.json
    
    # Extract Patient Data
    name = data.get('name', 'Unknown').strip()
    patient_id = data.get('patient_id', '').strip()
    
    if not patient_id:
        existing_patient = database.get_patient_by_name(name)
        if existing_patient:
            patient_id = existing_patient['patient_id']
        else:
            patient_id = str(uuid.uuid4())[:8]
    age = int(data.get('age', 0))
    gender = data.get('gender', 'Male')
    weight = float(data.get('weight', 0))
    hist_hypertension = 1 if 'hypertension' in data.get('history', []) else 0
    hist_diabetes = 1 if 'diabetes' in data.get('history', []) else 0
    hist_heart_disease = 1 if 'heart_disease' in data.get('history', []) else 0
    room_no = data.get('room_no', '').strip()
    bed_no = data.get('bed_no', '').strip()
    
    # Save patient
    patient_db_id = database.add_patient(patient_id, name, age, gender, weight, 
                                         hist_hypertension, hist_diabetes, hist_heart_disease, room_no, bed_no)
    
    # Prepare features for ML Model
    ml_input = {
        'age': age,
        'gender': 1 if gender == 'Male' else 0,
        'weight': weight,
        'history_hypertension': hist_hypertension,
        'history_diabetes': hist_diabetes,
        'history_heart_disease': hist_heart_disease,
        'heart_rate': float(data.get('heart_rate', 75)),
        'sys_bp': float(data.get('sys_bp', 120)),
        'dia_bp': float(data.get('dia_bp', 80)),
        'spo2': float(data.get('spo2', 98)),
        'temperature': float(data.get('temperature', 37.0)),
        'resp_rate': float(data.get('resp_rate', 16)),
        'chest_pain': 1 if 'chest_pain' in data.get('symptoms', []) else 0,
        'shortness_breath': 1 if 'shortness_breath' in data.get('symptoms', []) else 0,
        'fever': 1 if 'fever' in data.get('symptoms', []) else 0,
        'dizziness': 1 if 'dizziness' in data.get('symptoms', []) else 0,
        'fatigue': 1 if 'fatigue' in data.get('symptoms', []) else 0,
        'palpitations': 1 if 'palpitations' in data.get('symptoms', []) else 0,
        'nausea': 1 if 'nausea' in data.get('symptoms', []) else 0,
        'headache': 1 if 'headache' in data.get('symptoms', []) else 0,
    }
    
    # Create DataFrame for prediction mapping correctly to feature_cols
    df_input = pd.DataFrame([ml_input])[feature_cols]
    
    # Scale & Predict
    scaled_input = scaler.transform(df_input)
    prediction = int(model.predict(scaled_input)[0])
    probabilities = model.predict_proba(scaled_input)[0]
    confidence_score = float(max(probabilities) * 100)
    
    # Get Recommendations
    doctor, actions = determine_recommendations(prediction, ml_input)
    
    # Save Assessment to DB
    assessment_data = ml_input.copy()
    assessment_data['ai_risk_level'] = prediction
    assessment_data['ai_confidence'] = confidence_score
    assessment_data['recommended_doctor'] = doctor
    assessment_data['recommended_actions'] = actions
    
    database.add_assessment(patient_db_id, assessment_data)
    
    response = {
        'status': 'success',
        'patient_id': patient_id,
        'prediction': prediction,
        'confidence_score': round(confidence_score, 1),
        'recommended_doctor': doctor,
        'recommended_actions': actions
    }
    return jsonify(response)

@app.route('/dashboard')
@login_required
def dashboard():
    patient_id = request.args.get('patient_id')
    if not patient_id:
        return redirect(url_for('index'))
        
    patient_name, assessments = database.get_patient_history(patient_id)
    if not assessments:
        return redirect(url_for('index'))
        
    latest = assessments[0]
    patient = database.get_patient(patient_id)
    prescription = database.get_prescription_by_patient_db_id(patient['id']) if patient else None
    
    return render_template('dashboard.html', patient_id=patient_id, patient=patient, name=patient_name, data=latest, prescription=prescription)

@app.route('/api/prescription/<patient_id>', methods=['POST'])
@roles_required('doctor')
def api_save_prescription(patient_id):
    data = request.json
    prescription_text = data.get('prescription_text', '')
    instructions_text = data.get('instructions_text', '')
    
    patient = database.get_patient(patient_id)
    if not patient:
        return jsonify({'error': 'Patient not found'}), 404
        
    database.save_prescription(patient['id'], prescription_text, instructions_text, session.get('user_id'))
    return jsonify({'status': 'success'})

@app.route('/history')
@login_required
def history():
    patients = database.get_all_patients_with_latest_assessment()
    return render_template('history.html', patients=patients)

@app.route('/patient_history/<patient_id>')
@login_required
def patient_history(patient_id):
    name, assessments = database.get_patient_history(patient_id)
    if not assessments:
        return 'Patient not found', 404
        
    vitals_history = []
    labels = []
    for a in reversed(assessments[:5]): # Get last 5 for chart, oldest first
        labels.append(a['created_at'].split()[0])
        vitals_history.append({
            'hr': a['heart_rate'],
            'sys': a['sys_bp'],
            'dia': a['dia_bp'],
            'spo2': a['spo2']
        })
        
    return render_template('patient_history.html', name=name, patient_id=patient_id, 
                           assessments=assessments, chart_data={'labels': labels, 'data': vitals_history})

@app.route('/api/patient/<patient_id>')
@login_required
def api_get_patient(patient_id):
    patient = database.get_patient(patient_id)
    if patient:
        return jsonify(patient)
    return jsonify({'error': 'Not found'}), 404

@app.route('/edit_patient/<patient_id>', methods=['POST'])
@roles_required('nurse')
def edit_patient(patient_id):
    data = request.json
    name = data.get('name', 'Unknown').strip()
    age = int(data.get('age', 0))
    gender = data.get('gender', 'Male')
    weight = float(data.get('weight', 0))
    hist_hypertension = 1 if 'hypertension' in data.get('history', []) else 0
    hist_diabetes = 1 if 'diabetes' in data.get('history', []) else 0
    hist_heart_disease = 1 if 'heart_disease' in data.get('history', []) else 0
    room_no = data.get('room_no', '').strip()
    bed_no = data.get('bed_no', '').strip()
    
    database.update_patient(patient_id, name, age, gender, weight, hist_hypertension, hist_diabetes, hist_heart_disease, room_no, bed_no)
    
    return jsonify({'status': 'success'})

@app.route('/download_report/<patient_id>')
@login_required
def download_report(patient_id):
    name, assessments = database.get_patient_history(patient_id)
    if not assessments:
        return "Patient not found", 404
    latest = assessments[0]
    
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    p.setFont("Helvetica-Bold", 18)
    p.drawString(200, 750, "VitalSense AI - Medical Assessment Report")
    
    p.setFont("Helvetica", 12)
    p.drawString(50, 700, f"Patient Name: {name} (ID: {patient_id})")
    p.drawString(50, 680, f"Date: {latest['created_at']}")
    
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, 640, "AI Prediction Results:")
    p.setFont("Helvetica", 12)
    risk_labels = {0: "Stable", 1: "Attention Required", 2: "Critical"}
    p.drawString(50, 620, f"Risk Level: {risk_labels.get(latest['ai_risk_level'], 'Unknown')} (Confidence: {latest['ai_confidence']}%)")
    p.drawString(50, 600, f"Recommended Specialist: {latest['recommended_doctor']}")
    p.drawString(50, 580, f"Immediate Actions: {latest['recommended_actions']}")
    
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, 540, "Vital Signs:")
    p.setFont("Helvetica", 12)
    p.drawString(50, 520, f"Heart Rate: {latest['heart_rate']} bpm")
    p.drawString(50, 500, f"Blood Pressure: {latest['sys_bp']}/{latest['dia_bp']} mmHg")
    p.drawString(50, 480, f"SpO2: {latest['spo2']}%")
    p.drawString(50, 460, f"Temperature: {latest['temperature']} C")
    p.drawString(50, 440, f"Respiratory Rate: {latest['resp_rate']} breaths/min")
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=vitalsense_report_{patient_id}.pdf'
    return response

if __name__ == '__main__':
    app.run(debug=True, port=5000)
