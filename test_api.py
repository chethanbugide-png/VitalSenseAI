import requests
import json

url = "http://127.0.0.1:5000/predict"
data = {
    "name": "Jane Doe",
    "age": 65,
    "gender": "Female",
    "weight": 85,
    "heart_rate": 130, # High
    "sys_bp": 160,     # High
    "dia_bp": 100,
    "spo2": 88,        # Low
    "temperature": 38.5,
    "resp_rate": 25,
    "history": ["hypertension", "diabetes"],
    "symptoms": ["chest_pain", "shortness_breath"]
}

response = requests.post(url, json=data)
print("Status Code:", response.status_code)
print("Response Body is JSON?", "Yes" if response.headers.get('content-type') == 'application/json' else "No")
if response.status_code == 200:
    res_data = response.json()
    print("Patient ID:", res_data['patient_id'])
    print("Risk Level Prediction (expected 2 - Critical for these vitals):", res_data['prediction'])
    print("Confidence:", res_data['confidence_score'], "%")
    print("Recommended Doctor:", res_data['recommended_doctor'])
    
    # Test downloading PDF
    pdf_url = f"http://127.0.0.1:5000/download_report/{res_data['patient_id']}"
    pdf_res = requests.get(pdf_url)
    print("PDF Status Code:", pdf_res.status_code)
    print("PDF Content Type:", pdf_res.headers.get('content-type'))
else:
    print("Error:", response.text)
