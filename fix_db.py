import sqlite3
import uuid

def fix_empty_patient_ids():
    conn = sqlite3.connect('vitalsense.db')
    cursor = conn.cursor()
    # Find patients with empty patient_id
    cursor.execute("SELECT id FROM patients WHERE patient_id = '' OR patient_id IS NULL")
    rows = cursor.fetchall()
    
    updated_count = 0
    for r in rows:
        new_id = str(uuid.uuid4())[:8]
        cursor.execute("UPDATE patients SET patient_id = ? WHERE id = ?", (new_id, r[0]))
        updated_count += 1
        
    conn.commit()
    conn.close()
    print(f"Fixed {updated_count} patients with empty IDs.")

if __name__ == '__main__':
    fix_empty_patient_ids()
