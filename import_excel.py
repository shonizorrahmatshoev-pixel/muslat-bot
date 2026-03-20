# import_excel.py
import pandas as pd
import sqlite3
import os

def import_shipments(file_path='Order 1.24.2026 .xlsx', sheet_name='CLEAN_DATA'):
    """Simple import that accepts all valid-looking data"""
    conn = sqlite3.connect('muslat.db')
    c = conn.cursor()
    
    try:
        print(f"🔄 Loading {file_path} → Sheet '{sheet_name}'...")
        
        # Read from CLEAN_DATA sheet
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        
        if len(df) == 0:
            print("❌ Sheet is empty!")
            return
        
        # Clean column names
        df.columns = [col.strip().lower() for col in df.columns]
        print(f"✅ Found {len(df)} rows in Excel\n")
        
        added = 0
        skipped_tracking = 0
        skipped_phone = 0
        skipped_duplicates = 0
        
        print("📦 Processing shipments...\n")
        
        for idx, row in df.iterrows():
            # Extract values by position (first 3 columns)
            cols = list(df.columns)[:3]
            
            tracking = str(row[cols[0]]).strip() if len(cols) > 0 else ""
            client_name = str(row[cols[1]]).strip() if len(cols) > 1 else ""
            phone = str(row[cols[2]]).strip() if len(cols) > 2 else ""
            
            # Skip empty tracking numbers
            if not tracking or len(tracking) < 3:
                skipped_tracking += 1
                continue
            
            # Normalize tracking to uppercase
            tracking = tracking.upper()
            
            # Skip invalid names (empty, single letter, totals)
            if not client_name or len(client_name) < 2 or client_name.lower() == 'total':
                skipped_tracking += 1
                continue
            
            # Normalize phone
            phone = phone.strip()
            if phone.startswith('+'):
                pass  # Keep as is
            elif phone.startswith('992') and not phone.startswith('+992'):
                phone = '+' + phone  # Add missing +
            
            # Skip if no valid phone
            if not phone or not ('+' in phone or len(phone) >= 8):
                skipped_phone += 1
                continue
            
            # Insert into database (duplicates automatically ignored)
            try:
                c.execute("""
                    INSERT OR IGNORE INTO shipments 
                    (tracking_number, phone_number, client_name, status, telegram_id) 
                    VALUES (?, ?, ?, ?, NULL)
                """, (tracking, phone, client_name, "In Transit"))
                
                if c.rowcount > 0:
                    added += 1
                
                if added % 50 == 0:
                    print(f"⏳ Progress: {added} added...", end='\r')
                    
            except Exception as e:
                print(f"\n⚠️ Error inserting row {idx}: {str(e)}")
                skipped_duplicates += 1
        
        conn.commit()
        print(f"\n\n{'='*60}")
        print(f"🎉 Import Complete!")
        print(f"{'='*60}")
        print(f"✅ Successfully added: {added}")
        print(f"⚠️ Skipped - Invalid tracking: {skipped_tracking}")
        print(f"⚠️ Skipped - Invalid phone: {skipped_phone}")
        print(f"⚠️ Skipped - Duplicates: {skipped_duplicates}")
        print(f"📊 Total rows checked: {len(df)}")
        print(f"{'='*60}\n")
        
        # Show samples
        if added > 0:
            c.execute("SELECT tracking_number, client_name, phone_number FROM shipments ORDER BY tracking_number LIMIT 5")
            samples = c.fetchall()
            print("📝 First 5 imports:")
            for sample in samples:
                print(f"   {sample[0]} | {sample[1]} | {sample[2]}")
        
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
    except KeyError as e:
        print(f"❌ Column not found: {e}")
        print(f"Available columns: {list(df.columns)}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    import_shipments('Order 1.24.2026 .xlsx', 'CLEAN_DATA')