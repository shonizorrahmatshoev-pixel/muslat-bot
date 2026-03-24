import os
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///muslat.db")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Shipment(Base):
    """Shipments table"""
    __tablename__ = "shipments"
    
    id = Column(Integer, primary_key=True, index=True)
    tracking_number = Column(String(100), unique=True, nullable=False)
    client_name = Column(String(200))
    phone_number = Column(String(50))
    status = Column(String(50), default="In Transit")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class RegisteredUser(Base):
    """Registered users table"""
    __tablename__ = "registered_users"
    
    telegram_id = Column(Integer, primary_key=True)
    phone_number = Column(String(50), unique=True)
    name = Column(String(200))
    registered_at = Column(DateTime, default=datetime.utcnow)
    is_admin = Column(Integer, default=0)

def init_database():
    """Create tables if they don't exist"""
    Base.metadata.create_all(bind=engine)
    print("✅ PostgreSQL database initialized!")

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def register_user(telegram_id, phone_number, name="Unknown"):
    """Register a user with phone number"""
    db = SessionLocal()
    try:
        existing = db.query(RegisteredUser).filter_by(telegram_id=telegram_id).first()
        if existing:
            existing.phone_number = phone_number
            db.commit()
            return True
        else:
            new_user = RegisteredUser(
                telegram_id=telegram_id,
                phone_number=phone_number,
                name=name,
                is_admin=1 if int(telegram_id) == int(os.getenv("ADMIN_IDS", "0")) else 0
            )
            db.add(new_user)
            db.commit()
            return True
    except Exception as e:
        print(f"Error registering user: {e}")
        return False
    finally:
        db.close()

def check_user_registered(telegram_id):
    """Check if user is registered"""
    db = SessionLocal()
    try:
        user = db.query(RegisteredUser).filter_by(telegram_id=telegram_id).first()
        return user is not None
    finally:
        db.close()

def get_user_info(telegram_id):
    """Get user info by telegram ID"""
    db = SessionLocal()
    try:
        user = db.query(RegisteredUser).filter_by(telegram_id=telegram_id).first()
        if user:
            return {
                'telegram_id': user.telegram_id,
                'phone_number': user.phone_number,
                'name': user.name,
                'is_admin': bool(user.is_admin)
            }
        return None
    finally:
        db.close()

def add_shipment(tracking_number, client_name, phone_number, status="In Transit"):
    """Add shipment to database"""
    db = SessionLocal()
    try:
        existing = db.query(Shipment).filter_by(tracking_number=tracking_number).first()
        if existing:
            existing.client_name = client_name
            existing.phone_number = phone_number
            existing.status = status
            existing.updated_at = datetime.utcnow()
            db.commit()
            return True
        else:
            new_shipment = Shipment(
                tracking_number=tracking_number,
                client_name=client_name,
                phone_number=phone_number,
                status=status
            )
            db.add(new_shipment)
            db.commit()
            return True
    except Exception as e:
        print(f"Error adding shipment: {e}")
        return False
    finally:
        db.close()

def get_shipment_info(tracking_number, phone_number=None):
    """Get shipment info by tracking number"""
    db = SessionLocal()
    try:
        result = db.query(Shipment).filter_by(tracking_number=tracking_number).first()
        if result:
            return {
                'tracking_number': result.tracking_number,
                'client_name': result.client_name,
                'phone_number': result.phone_number,
                'status': result.status,
                'created_at': str(result.created_at),
                'updated_at': str(result.updated_at)
            }
        return None
    finally:
        db.close()

def list_all_shipments(limit=50):
    """List all shipments"""
    db = SessionLocal()
    try:
        shipments = db.query(Shipment).order_by(Shipment.updated_at.desc()).limit(limit).all()
        result = []
        for s in shipments:
            result.append({
                'tracking_number': s.tracking_number,
                'client_name': s.client_name,
                'phone_number': s.phone_number,
                'status': s.status,
                'updated_at': str(s.updated_at)
            })
        return result
    finally:
        db.close()

def get_shipments_by_phone(phone):
    """Filter shipments by phone number"""
    db = SessionLocal()
    try:
        shipments = db.query(Shipment).filter(Shipment.phone_number.contains(phone)).order_by(Shipment.updated_at.desc()).all()
        result = []
        for s in shipments:
            result.append({
                'tracking_number': s.tracking_number,
                'client_name': s.client_name,
                'phone_number': s.phone_number,
                'status': s.status,
                'updated_at': str(s.updated_at)
            })
        return result
    finally:
        db.close()