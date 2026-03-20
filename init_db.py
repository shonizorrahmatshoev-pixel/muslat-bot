# init_db.py
import sqlite3

def create_tables():
    """Create database tables if they don't exist"""
    conn = sqlite3.connect('muslat.db')
    c = conn.cursor()
    
    # Create users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (telegram_id INTEGER PRIMARY KEY, 
                  phone_number TEXT UNIQUE, 
                  name TEXT)''')
    
    # Create shipments table
    c.execute('''CREATE TABLE IF NOT EXISTS shipments
                 (tracking_number TEXT PRIMARY KEY, 
                  phone_number TEXT, 
                  client_name TEXT, 
                  status TEXT DEFAULT 'In Transit',
                  telegram_id INTEGER)''')
    
    conn.commit()
    conn.close()
    print("✅ Database tables created successfully!")

if __name__ == '__main__':
    create_tables()