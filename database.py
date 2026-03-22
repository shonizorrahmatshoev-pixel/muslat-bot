import sqlite3
import os
from datetime import datetime

DATABASE_NAME = "muslat.db"

def get_connection():
    """Get database connection"""
    return sqlite3.connect(DATABASE_NAME)

def init_database():
    """Initialize database tables"""
    conn = get_connection()
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
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")

def add_shipment_info(tracking_number, client_name, phone_number, status="In Transit"):
    """Add shipment to database"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if already exists
        cursor.execute('SELECT tracking_number FROM shipments WHERE tracking_number = ?', (tracking_number,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing record
            cursor.execute('''
                UPDATE shipments 
                SET client_name = ?, phone_number = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE tracking_number = ?
            ''', (client_name, phone_number, status, tracking_number))
            affected = cursor.rowcount
        else:
            # Insert new record
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

def get_shipment_info(tracking_number, phone_number):
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

def list_all_shipments():
    """List all shipments in database"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT tracking_number, client_name, phone_number, status, updated_at
            FROM shipments
            ORDER BY updated_at DESC
        ''')
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