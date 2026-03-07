import pandas as pd
import numpy as np
import random
import os

# Set seed for reproducibility
np.random.seed(42)
random.seed(42)

NUM_SAMPLES = 100000

def generate_patient():
    # Base features
    age = np.random.randint(18, 90)
    gender = np.random.choice(['Male', 'Female'])
    weight = np.random.uniform(50.0, 120.0) # kg
    
    # History (categorical/boolean)
    history_hypertension = np.random.choice([0, 1], p=[0.7, 0.3])
    history_diabetes = np.random.choice([0, 1], p=[0.8, 0.2])
    history_heart_disease = np.random.choice([0, 1], p=[0.85, 0.15])
    
    # Initialize basic vitals as normal
    hr = np.random.normal(75, 10)
    sys_bp = np.random.normal(115, 10)
    dia_bp = np.random.normal(75, 8)
    spo2 = np.random.normal(98, 1.5)
    temp = np.random.normal(36.8, 0.4)
    resp_rate = np.random.normal(16, 2)
    
    # Symptoms initialization (0 = No, 1 = Yes)
    chest_pain = 0
    shortness_breath = 0
    fever = 0
    dizziness = 0
    fatigue = 0
    palpitations = 0
    nausea = 0
    headache = 0
    
    # Determine risk category logic first, then shape features to match
    # 0: Stable (60%), 1: Attention Required (30%), 2: Critical (10%)
    risk_level = np.random.choice([0, 1, 2], p=[0.6, 0.3, 0.1])
    
    if risk_level == 0:
        # Stable
        # Keep vitals mostly normal
        hr = np.clip(hr, 60, 95)
        spo2 = np.clip(spo2, 95, 100)
        sys_bp = np.clip(sys_bp, 90, 125)
        dia_bp = np.clip(dia_bp, 60, 80)
        # Few mild symptoms
        fatigue = np.random.choice([0, 1], p=[0.8, 0.2])
        headache = np.random.choice([0, 1], p=[0.8, 0.2])
        
    elif risk_level == 1:
        # Attention Required
        # Some vitals slightly off
        if random.random() < 0.5:
            hr = np.random.uniform(95, 115)
            palpitations = 1
        if random.random() < 0.5:
            sys_bp = np.random.uniform(130, 150)
            dia_bp = np.random.uniform(85, 95)
            headache = 1
            dizziness = np.random.choice([0, 1], p=[0.5, 0.5])
        if random.random() < 0.3:
            temp = np.random.uniform(37.5, 38.5)
            fever = 1
        
        spo2 = np.random.uniform(92, 95) # Slightly low
        fatigue = 1
        
    else:
        # Critical
        # Vitals significantly off
        critical_type = random.choice(['cardiac', 'respiratory', 'infection'])
        
        if critical_type == 'cardiac':
            hr = np.random.uniform(120, 180) # Tachycardia
            sys_bp = np.random.choice([np.random.uniform(70, 90), np.random.uniform(160, 200)])
            dia_bp = np.random.choice([np.random.uniform(40, 60), np.random.uniform(100, 120)])
            chest_pain = 1
            palpitations = 1
            dizziness = 1
            spo2 = np.random.uniform(85, 92)
            
        elif critical_type == 'respiratory':
            spo2 = np.random.uniform(75, 89) # Severe hypoxia
            resp_rate = np.random.uniform(25, 40) # Tachypnea
            shortness_breath = 1
            hr = np.random.uniform(100, 130)
            
        else: # Infection/Sepsis
            temp = np.random.uniform(39.0, 41.0) # High fever
            hr = np.random.uniform(110, 140)
            sys_bp = np.random.uniform(70, 90) # Hypotension
            fever = 1
            fatigue = 1
            nausea = np.random.choice([0, 1], p=[0.2, 0.8])
            
    # Compile features
    patient = {
        'age': age,
        'gender': 1 if gender == 'Male' else 0,
        'weight': round(weight, 1),
        'history_hypertension': history_hypertension,
        'history_diabetes': history_diabetes,
        'history_heart_disease': history_heart_disease,
        'heart_rate': round(hr, 0),
        'sys_bp': round(sys_bp, 0),
        'dia_bp': round(dia_bp, 0),
        'spo2': round(spo2, 1),
        'temperature': round(temp, 1),
        'resp_rate': round(resp_rate, 0),
        'chest_pain': chest_pain,
        'shortness_breath': shortness_breath,
        'fever': fever,
        'dizziness': dizziness,
        'fatigue': fatigue,
        'palpitations': palpitations,
        'nausea': nausea,
        'headache': headache,
        'risk_level': risk_level
    }
    return patient

def main():
    print(f"Generating {NUM_SAMPLES} patient records...")
    data = [generate_patient() for _ in range(NUM_SAMPLES)]
    df = pd.DataFrame(data)
    
    # Double check values constraints
    df['heart_rate'] = df['heart_rate'].clip(lower=30, upper=220)
    df['sys_bp'] = df['sys_bp'].clip(lower=50, upper=250)
    df['dia_bp'] = df['dia_bp'].clip(lower=30, upper=150)
    df['spo2'] = df['spo2'].clip(lower=50, upper=100)
    df['temperature'] = df['temperature'].clip(lower=30.0, upper=43.0)
    df['resp_rate'] = df['resp_rate'].clip(lower=5, upper=60)
    
    os.makedirs('ml/data', exist_ok=True)
    df.to_csv('ml/data/synthetic_patients.csv', index=False)
    print("Dataset saved to ml/data/synthetic_patients.csv")
    print("\nDataset split:")
    print(df['risk_level'].value_counts(normalize=True) * 100)

if __name__ == "__main__":
    main()
