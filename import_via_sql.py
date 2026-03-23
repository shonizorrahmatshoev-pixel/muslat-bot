import sqlite3
import pandas as pd

DATABASE_NAME = "muslat.db"

def import_shipments(excel_file="Order 1.24.2026.xlsx"):
    """Directly import Excel to railway database"""
    
    try:
        # Read Excel
        df = pd.read_excel(excel_file)
        
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        imported = 0
        
        for idx, row in df.iterrows():
            tracking = str(row.iloc[0]).strip()
            client_name = str(row.iloc[1]).strip()
            phone = str(row.iloc[2]).strip()
            status = str(row.iloc[3]).strip() if len(row) > 3 else "In Transit"
            
            cursor.execute('''
                INSERT OR REPLACE INTO shipments 
                (tracking_number, client_name, phone_number, status)
                VALUES (?, ?, ?, ?)
            ''', (tracking, client_name, phone, status))
            
            imported += 1
        
        conn.commit()
        conn.close()
        
        print(f"✅ Imported {imported} shipments!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    import_shipments()