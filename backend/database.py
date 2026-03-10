import sqlite3
from datetime import datetime, timedelta
import pandas as pd

DB_NAME = "sentinel_history.db"

def init_db():
    """Initialize the database with the updated schema (Metadata + Velocity)."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            customer_id TEXT,
            ip_address TEXT,
            txn_type TEXT,
            amount REAL,
            risk_score TEXT,
            velocity_flag INTEGER,
            explanation TEXT
        )
    ''')
    conn.commit()
    conn.close()

def log_transaction(customer_id, ip, txn_data, risk_score, velocity_flag, explanation):
    """Save a new transaction with user metadata."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    c.execute('''
        INSERT INTO transactions 
        (timestamp, customer_id, ip_address, txn_type, amount, risk_score, velocity_flag, explanation)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        timestamp, 
        customer_id, 
        ip, 
        txn_data.type, 
        txn_data.amount, 
        risk_score, 
        velocity_flag, 
        explanation
    ))
    
    conn.commit()
    conn.close()

def get_customer_velocity(customer_id):
    """Count how many transactions this specific user made in the last hour."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    one_hour_ago = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    
    c.execute('''
        SELECT count(*) FROM transactions 
        WHERE customer_id = ? AND timestamp > ?
    ''', (customer_id, one_hour_ago))
    
    result = c.fetchone()
    count = result[0] if result else 0
    
    conn.close()
    return count

def get_recent_transactions(limit=50):
    """Fetch the last N transactions for the History Dashboard."""
    conn = sqlite3.connect(DB_NAME)
    try:
        df = pd.read_sql_query(f"SELECT * FROM transactions ORDER BY id DESC LIMIT {limit}", conn)
    except Exception:
        # Fallback if table doesn't exist yet
        df = pd.DataFrame()
    finally:
        conn.close()
    return df