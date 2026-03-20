# check_imports.py
import sqlite3

conn = sqlite3.connect('muslat.db')
c = conn.cursor()

# Count total shipments
c.execute("SELECT COUNT(*) FROM shipments")
count = c.fetchone()[0]

print(f"\n🎉 Your Muslat Express Bot!")
print(f"{'='*50}")
print(f"📦 Total Shipments in Database: {count}")
print(f"👥 Unique Customers: {c.execute('SELECT COUNT(DISTINCT client_name) FROM shipments').fetchone()[0]}")
print(f"{'='*50}\n")

# Show sample clients
print("📝 Sample Shipment Tracking:")
for track in c.execute("SELECT tracking_number, client_name, status FROM shipments LIMIT 3"):
    print(f"   📬 {track[0]} | 👤 {track[1]} | 🚚 {track[2]}")

conn.close()