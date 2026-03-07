import app
import database

app.app.config['TESTING'] = True
client = app.app.test_client()

# Note: We need a patient in the database to test. Assuming one exists or we'll get a 404.
patients = database.get_db_connection().execute('SELECT patient_id FROM patients LIMIT 1').fetchone()
if not patients:
    print("No patients in DB to test with. Please add a patient first.")
    exit(0)

patient_id = patients['patient_id']

# Function to login via test client
def login(username, password='password123'):
    return client.post('/login', data={'username': username, 'password': password}, follow_redirects=True)

# Test as nurse - should be forbidden to save prescription
login('nurse')
resp = client.post(f"/api/prescription/{patient_id}", json={
    'prescription_text': 'Aspirin 81mg',
    'instructions_text': 'Take daily'
})
print("Nurse save prescription status:", resp.status_code) # Should be 403

# Logout
client.get('/logout')

# Test as doctor - should be success
login('doctor')
resp = client.post(f"/api/prescription/{patient_id}", json={
    'prescription_text': 'Lisinopril 10mg',
    'instructions_text': 'Take daily in the morning'
})
print("Doctor save prescription status:", resp.status_code) # Should be 200

# Verify it was saved in DB
prescription = database.get_db_connection().execute(
    'SELECT * FROM prescriptions p JOIN patients pat ON p.patient_db_id = pat.id WHERE pat.patient_id = ?', 
    (patient_id,)
).fetchone()
print("Saved prescription in DB:")
if prescription:
    d = dict(prescription)
    # Don't print timestamps as they vary
    d.pop('created_at', None)
    d.pop('updated_at', None)
    print(d)
else:
    print("None")

