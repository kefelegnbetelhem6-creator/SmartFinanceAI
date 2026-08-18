import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import requests
import re
import os
import json
import plotly.express as px
from datetime import datetime
from dotenv import load_dotenv

# Configuration
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DATABASE_FILE = 'finance_manager.db'

st.set_page_config(page_title="Intelligent Finance Suite", page_icon="⚖️", layout="wide")

# --- Security & Authentication ---

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def verify_password_hash(password, hashed_text):
    return hash_password(password) == hashed_text

def validate_password_strength(password):
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    return True, "Strong"

# --- Database Management ---

def init_db():
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT, category TEXT, description TEXT, 
                  amount REAL, type TEXT, username TEXT)''')
    conn.commit()
    conn.close()

def register_user(username, password):
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO users (username, password) VALUES (?,?)", (username, hash_password(password)))
    conn.commit()
    conn.close()

def authenticate_user(username, password):
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username = ?", (username,))
    data = c.fetchone()
    conn.close()
    if data:
        return verify_password_hash(password, data[0])
    return False

def add_entry(category, description, amount, entry_type, username):
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    date_stamp = datetime.now().strftime("%Y-%m-%d")
    c.execute("INSERT INTO transactions (date, category, description, amount, type, username) VALUES (?,?,?,?,?,?)",
              (date_stamp, category, description, amount, entry_type, username))
    conn.commit()
    conn.close()

def remove_entry(entry_id):
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM transactions WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()

def load_user_records(username):
    conn = sqlite3.connect(DATABASE_FILE)
    query = "SELECT * FROM transactions WHERE username = ?"
    df = pd.read_sql_query(query, conn, params=(username,))
    conn.close()
    return df

# --- AI Integration Service (Optimized for Deployment) ---

def fetch_ai_analysis(df):
    if not GROQ_API_KEY:
        return "System Error: API Key not found in environment."
    
    summary_data = df.groupby(['type', 'category'])['amount'].sum().to_string()
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.1-8b-instant", # Using the most stable high-speed model
        "messages": [
            {
                "role": "system", 
                "content": "You are a direct financial consultant. Analyze the data and provide 3 short bullet points of advice. No conversational filler. English only."
            },
            {"role": "user", "content": f"Data:\n{summary_data}"}
        ],
        "temperature": 0.1
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        return f"Service Notification: HTTP {response.status_code}. The AI engine is updating. Please try again in a moment."
    except Exception:
        return "Connection Timeout: Unable to reach AI server."

# --- Main Application Logic ---

init_db()

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 Secure Portal | Intelligent Finance")
    mode = st.tabs(["Login", "Create Account"])
    
    with mode[0]:
        user_in = st.text_input("Username", key="login_user")
        pass_in = st.text_input("Password", type="password", key="login_pass")
        if st.button("Access Dashboard"):
            if authenticate_user(user_in, pass_in):
                st.session_state.authenticated = True
                st.session_state.current_user = user_in
                st.rerun()
            else:
                st.error("Authentication failed. Please check your credentials.")

    with mode[1]:
        new_user = st.text_input("New Username")
        new_pass = st.text_input("New Password", type="password")
        if st.button("Register Account"):
            is_strong, msg = validate_password_strength(new_pass)
            if not is_strong:
                st.warning(msg)
            else:
                try:
                    register_user(new_user, new_pass)
                    st.success("Account created. You can now login.")
                except sqlite3.IntegrityError:
                    st.error("Username is already taken.")
    st.stop()

# --- Post-Login Dashboard ---

st.title(f"💼 Control Panel | {st.session_state.current_user}")

with st.sidebar:
    st.header("New Transaction")
    entry_type = st.selectbox("Type", ["Expense", "Income"])
    categories = ["Food", "Housing", "Transport", "Income/Salary", "Health", "Shopping", "Education", "Other"]
    cat = st.selectbox("Category", categories)
    amt = st.number_input("Amount (ETB)", min_value=1.0, step=100.0)
    note = st.text_input("Note")
    
    if st.button("Record Transaction"):
        add_entry(cat, note, amt, entry_type, st.session_state.current_user)
        st.toast("Database Updated")
        st.rerun()
    
    st.divider()
    budget = st.number_input("Monthly Budget Target (ETB)", value=10000.0)
    
    if st.button("Sign Out"):
        st.session_state.authenticated = False
        st.rerun()

df_records = load_user_records(st.session_state.current_user)

if not df_records.empty:
    tab_overview, tab_ledger, tab_ai = st.tabs(["📊 Analytics", "📂 Ledger", "🧠 AI Consultant"])
    
    with tab_overview:
        total_in = df_records[df_records['type'] == 'Income']['amount'].sum()
        total_out = df_records[df_records['type'] == 'Expense']['amount'].sum()
        
        if total_out > budget:
            st.error(f"⚠️ Budget Alert: Limit exceeded by {total_out - budget:,.2f} ETB")
        else:
            st.success(f"✅ Budget Status: {budget - total_out:,.2f} ETB remaining")

        m_cols = st.columns(3)
        m_cols[0].metric("Total Income", f"{total_in:,.2f}")
        m_cols[1].metric("Total Expenses", f"{total_out:,.2f}")
        m_cols[2].metric("Net Balance", f"{total_in - total_out:,.2f}")

        c_cols = st.columns(2)
        with m_cols[0]: # Re-using column logic for charts
            expense_only = df_records[df_records['type'] == 'Expense']
            if not expense_only.empty:
                fig_pie = px.pie(expense_only, values='amount', names='category', title="Spending by Category")
                st.plotly_chart(fig_pie, use_container_width=True)
        with c_cols[1]:
            fig_bar = px.bar(df_records, x='date', y='amount', color='type', barmode='group', title="Financial History")
            st.plotly_chart(fig_bar, use_container_width=True)

    with tab_ledger:
        st.subheader("Data Records")
        st.download_button("Download Statement (CSV)", data=df_records.to_csv(index=False).encode('utf-8'), file_name="statement.csv")
        
        for idx, row in df_records.iterrows():
            r_cols = st.columns([1, 2, 2, 2, 1])
            r_cols[0].write(row['date'])
            r_cols[1].write(row['category'])
            r_cols[2].write(f"{row['amount']:,.2f}")
            r_cols[3].write(row['type'])
            if r_cols[4].button("Delete", key=f"del_{row['id']}"):
                remove_entry(row['id'])
                st.rerun()

    with tab_ai:
        st.subheader("AI Financial Intelligence")
        if st.button("Generate Expert Report"):
            with st.spinner("Analyzing patterns..."):
                advice = fetch_ai_analysis(df_records)
                st.markdown(advice)
else:
    st.info("Your dashboard is currently empty. Please add a transaction to begin.")