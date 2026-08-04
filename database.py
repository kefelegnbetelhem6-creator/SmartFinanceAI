import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('finance_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT,
                  category TEXT,
                  description TEXT,
                  amount REAL,
                  type TEXT)''')
    conn.commit()
    conn.close()

def add_transaction(category, description, amount, trans_type):
    conn = sqlite3.connect('finance_data.db')
    c = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO transactions (date, category, description, amount, type) VALUES (?, ?, ?, ?, ?)",
              (date, category, description, amount, trans_type))
    conn.commit()
    conn.close()

def get_all_transactions():
    conn = sqlite3.connect('finance_data.db')
    c = conn.cursor()
    c.execute("SELECT * FROM transactions")
    data = c.fetchall()
    conn.close()
    return data