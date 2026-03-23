import sqlite3
from datetime import datetime

DATABASE_NAME = "muslat.db"

def get_connection():
    """Get database connection"""
    return sqlite3.connect(DATABASE_NAME)

def init_database():
    """Initialize database tables & register admins"""
    import os
    
    DATABASE_NAME = "muslat.db"
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # Create shipments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shipments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tracking_number TEXT UNIQUE NOT NULL,
            client_name TEXT,
            phone_number TEXT,
            status TEXT DEFAULT 'In Transit',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    print("✅ Database tables created!")
    
    # MIGRATION: Add missing columns if they don't exist
    try:
        cursor.execute("ALTER TABLE shipments ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        print("✅ Column updated_at handled!")
    except Exception as e:
        print(f"⚠️ Column may already exist: {e}")
    
    try:
        cursor.execute("ALTER TABLE shipments ADD COLUMN client_name TEXT")
        print("✅ Column client_name handled!")
    except Exception as e:
        print(f"⚠️ Column may already exist: {e}")
    
    try:
        cursor.execute("ALTER TABLE shipments ADD COLUMN phone_number TEXT")
        print("✅ Column phone_number handled!")
    except Exception as e:
        print(f"⚠️ Column may already exist: {e}")
    
    # Create registered_users table FIRST
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registered_users (
            telegram_id INTEGER PRIMARY KEY,
            phone_number TEXT UNIQUE NOT NULL,
            name TEXT,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_admin INTEGER DEFAULT 0
        )
    ''')
    print("✅ Users table created!")
    
    # ADD YOUR ADMIN ID RIGHT NOW! ⭐
    try:
        admin_id = int(1273176859)  # YOUR ACTUAL CHAT ID FROM TELEGRAM
        cursor.execute('''
            INSERT OR REPLACE INTO registered_users 
            (telegram_id, phone_number, name, is_admin)
            VALUES (?, ?, ?, ?)
        ''', (admin_id, "Admin Account", "Shakhnoz R", 1))
        print("✅ Added YOU as admin!")
    except Exception as e:
        print(f"⚠️ Could not add admin: {e}")
    
    # COMMIT ALL CHANGES FIRST
    conn.commit()
    print("✅ Database committed successfully!")
    
    # CLOSE CONNECTION LAST
    conn.close()
    print("✅ Database initialized successfully!")

def register_user(telegram_id, phone_number, name="Unknown"):
    """Register a user with phone number"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT telegram_id FROM registered_users WHERE telegram_id = ?', (telegram_id,))
        if cursor.fetchone():
            cursor.execute('''
                UPDATE registered_users SET phone_number = ?
                WHERE telegram_id = ?
            ''', (phone_number, telegram_id))
            affected = cursor.rowcount
        else:
            cursor.execute('''
                INSERT INTO registered_users (telegram_id, phone_number, name)
                VALUES (?, ?, ?)
            ''', (telegram_id, phone_number, name))
            affected = cursor.rowcount
        
        conn.commit()
        conn.close()
        return affected > 0
        
    except Exception as e:
        print(f"Error registering user: {e}")
        return False

def get_user_info(telegram_id):
    """Get user info by telegram ID"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT telegram_id, phone_number, name, is_admin
            FROM registered_users
            WHERE telegram_id = ?
        ''', (telegram_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'telegram_id': result[0],
                'phone_number': result[1],
                'name': result[2],
                'is_admin': result[3] == 1
            }
        return None
        
    except Exception as e:
        print(f"Error getting user: {e}")
        return None

def check_user_registered(telegram_id):
    """Check if user is registered"""
    info = get_user_info(telegram_id)
    return info is not None

def is_admin(telegram_id):
    """Check if user is admin"""
    info = get_user_info(telegram_id)
    return info is not None and info.get('is_admin', 0) == 1

def add_shipment_info(tracking_number, client_name, phone_number, status="In Transit"):
    """Add or update shipment in database"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT tracking_number FROM shipments WHERE tracking_number = ?', (tracking_number,))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute('''
                UPDATE shipments 
                SET client_name = ?, phone_number = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE tracking_number = ?
            ''', (client_name, phone_number, status, tracking_number))
            affected = cursor.rowcount
        else:
            cursor.execute('''
                INSERT INTO shipments (tracking_number, client_name, phone_number, status)
                VALUES (?, ?, ?, ?)
            ''', (tracking_number, client_name, phone_number, status))
            affected = cursor.rowcount
        
        conn.commit()
        conn.close()
        return affected > 0
        
    except Exception as e:
        print(f"Error adding shipment: {e}")
        return False

def get_shipment_info(tracking_number, phone_number=None):
    """Get shipment info by tracking number and/or phone"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT tracking_number, client_name, phone_number, status, created_at, updated_at
            FROM shipments
        '''
        
        params = []
        conditions = []
        
        if tracking_number:
            conditions.append('tracking_number = ?')
            params.append(tracking_number)
            
        if phone_number:
            conditions.append('phone_number = ?')
            params.append(phone_number)
            
        if conditions:
            query += ' WHERE ' + ' OR '.join(conditions)
        
        cursor.execute(query, params)
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'tracking_number': result[0],
                'client_name': result[1],
                'phone_number': result[2],
                'status': result[3],
                'created_at': result[4],
                'updated_at': result[5]
            }
        return None
        
    except Exception as e:
        print(f"Error getting shipment: {e}")
        return None

def list_all_shipments(limit=50):
    """List all shipments in database"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT tracking_number, client_name, phone_number, status, updated_at
            FROM shipments
            ORDER BY updated_at DESC
            LIMIT ?
        ''', (limit,))
        results = cursor.fetchall()
        conn.close()
        
        shipments = []
        for row in results:
            shipments.append({
                'tracking_number': row[0],
                'client_name': row[1],
                'phone_number': row[2],
                'status': row[3],
                'updated_at': row[4]
            })
            
        return shipments
        
    except Exception as e:
        print(f"Error listing shipments: {e}")
        return []