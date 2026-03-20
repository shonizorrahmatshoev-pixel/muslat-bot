import sqlite3

def init_db():
    conn = sqlite3.connect('muslat.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (telegram_id INTEGER PRIMARY KEY, 
                  phone_number TEXT UNIQUE, 
                  name TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS shipments
                 (tracking_number TEXT PRIMARY KEY, 
                  phone_number TEXT, 
                  client_name TEXT, 
                  status TEXT DEFAULT 'Pending',
                  telegram_id INTEGER)''')
    
    conn.commit()
    conn.close()

def add_user(telegram_id, phone_number, name):
    conn = sqlite3.connect('muslat.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users VALUES (?, ?, ?)", (telegram_id, phone_number, name))
        c.execute("UPDATE shipments SET telegram_id = ? WHERE phone_number = ?", (telegram_id, phone_number))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user_by_phone(phone_number):
    conn = sqlite3.connect('muslat.db')
    c = conn.cursor()
    c.execute("SELECT telegram_id FROM users WHERE phone_number = ?", (phone_number,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def add_shipment(tracking, phone, name, status="In Transit"):
    conn = sqlite3.connect('muslat.db')
    c = conn.cursor()
    telegram_id = get_user_by_phone(phone)
    try:
        c.execute("INSERT INTO shipments VALUES (?, ?, ?, ?, ?)", 
                  (tracking, phone, name, status, telegram_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_shipment(tracking_number, phone_number):
    conn = sqlite3.connect('muslat.db')
    c = conn.cursor()
    c.execute("SELECT status, client_name FROM shipments WHERE tracking_number = ? AND phone_number = ?", 
              (tracking_number, phone_number))
    result = c.fetchone()
    conn.close()
    return result

def get_all_shipments_by_phone(phone_number):
    conn = sqlite3.connect('muslat.db')
    c = conn.cursor()
    c.execute("SELECT tracking_number, status FROM shipments WHERE phone_number = ?", (phone_number,))
    results = c.fetchall()
    conn.close()
    return results

init_db()