# upload_data.py
import pandas as pd
import database as db

def clean_phone_number(phone):
    """Normalize phone numbers to +992 format"""
    if not phone or phone == '' or str(phone).strip() == '?' or str(phone).strip() == '':
        return None
    
    phone = str(phone).replace(' ', '').replace('-', '').replace(' ', '')
    
    # Remove any non-numeric characters except +
    phone = ''.join(c for c in phone if c.isdigit() or c == '+')
    
    # If starts with 992 without +, add it
    if phone.startswith('992'):
        phone = '+' + phone
    
    # Check for valid length (Tajikistan numbers should be around 9 digits after country code)
    if phone.startswith('+992'):
        digits_only = phone.replace('+', '')
        if len(digits_only) >= 10:
            return phone[:15]  # Limit max length
    
    return phone

def upload_excel(file_path='uploads.xlsx'):
    """Load Excel data into database"""
    try:
        print("🔄 Loading Excel file...", end='')
        df = pd.read_excel(file_path)
        
        # Normalize column names to lowercase
        df.columns = [col.strip().lower() for col in df.columns]
        print("✅")
        
        records_added = 0
        records_skipped = 0
        
        print("\n📦 Processing shipments...\n")
        
        for index, row in df.iterrows():
            # Get tracking number (try different column name variations)
            tracking = None
            for col in ['original tracking no.', 'tracking', 'original tracking no.', 'no']:
                if col in df.columns:
                    val = str(row[col]).strip() if pd.notna(row[col]) else ""
                    if val and val not in ['', '?', None]:
                        tracking = val.upper().strip()
                        break
            
            if not tracking:
                records_skipped += 1
                continue
            
            # Get client name
            client_name = None
            for col in ['client name', 'name', 'client']:
                if col in df.columns:
                    val = str(row[col]).strip() if pd.notna(row[col]) else ""
                    if val and val not in ['', '?', None]:
                        client_name = val.strip()
                        break
            
            # Get phone number
            phone = None
            for col in ['client phone no.', 'phone', 'client phone no.', 'phone no.']:
                if col in df.columns:
                    val = str(row[col]).strip() if pd.notna(row[col]) else ""
                    if val and val not in ['', '?', None]:
                        phone = clean_phone_number(val)
                        break
            
            # Skip if no tracking or phone
            if not tracking or not client_name or not phone:
                records_skipped += 1
                continue
            
            # Add to database
            success = db.add_shipment(tracking, phone, client_name, "In Transit")
            
            if success:
                records_added += 1
                
                if records_added % 10 == 0:
                    print(f"⏳ Progress: {records_added} added", end='\r')
            
        print(f"\n\n🎉 Upload Complete!")
        print(f"✅ Added: {records_added}")
        print(f"⚠️ Skipped: {records_skipped}")
        
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == '__main__':
    # Upload file you drop here
    upload_excel()