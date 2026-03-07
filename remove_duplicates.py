import sqlite3

def consolidate_duplicates():
    conn = sqlite3.connect('vitalsense.db')
    cursor = conn.cursor()
    
    # Get all patients
    cursor.execute("SELECT id, LOWER(name) as lname FROM patients ORDER BY id ASC")
    patients = cursor.fetchall()
    
    # Map name to primary patient ID (the first one encountered)
    primary_ids = {}
    duplicates = []
    
    for p_id, lname in patients:
        if lname not in primary_ids:
            primary_ids[lname] = p_id
        else:
            duplicates.append((p_id, primary_ids[lname]))
    
    updated_assessments = 0
    deleted_patients = 0
    
    for dup_id, primary_id in duplicates:
        # Move all assessments from duplicate to primary
        cursor.execute("UPDATE assessments SET patient_db_id = ? WHERE patient_db_id = ?", (primary_id, dup_id))
        updated_assessments += cursor.rowcount
        
        # Delete the duplicate patient
        cursor.execute("DELETE FROM patients WHERE id = ?", (dup_id,))
        deleted_patients += 1
        
    conn.commit()
    conn.close()
    
    if deleted_patients > 0:
        print(f"Successfully consolidated {deleted_patients} duplicate patients.")
        print(f"Moved {updated_assessments} assessments to their primary patient records.")
    else:
        print("No duplicate patients found.")

if __name__ == '__main__':
    consolidate_duplicates()
