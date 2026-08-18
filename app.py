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

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DATABASE_FILE = 'finance_manager.db'

# Page Configuration
st.set_page_config(page_title="Intelligent Finance Suite", page_icon="⚖️", layout="wide")

# --- Security & Authentication Logic ---

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def verify_password_hash(password, hashed_text):
    return hash_password(password) == hashed_text

def validate_password_strength(password):
    """Ensures password meet security standards: 6+ chars, 1 digit, 1 uppercase."""
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

# --- AI Integration Service ---

def fetch_ai_analysis(df):
    if not GROQ_API_KEY:
        return "Service Error: Connectivity issue."
    
    # Flattening data for the LLM context
    summary_data = df.groupby(['type', 'category'])['amount'].sum().to_string()
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system", 
                "content": "You are a professional financial consultant. Analyze the data and provide 3 concise, high-impact saving strategies. Use professional English. No introductory text."
            },
            {"role": "user", "content": f"Dataset Summary:\n{summary_data}"}
        ],
        "temperature": 0.1
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        return f"AI Error: HTTP {response.status_code}"
    except Exception:
        return "AI Engine unreachable."

# --- Application Main Interface ---

init_db()

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# --- Auth Screen ---
if not st.session_state.authenticated:
    st.title("🔐 Intelligent Finance Suite - Secure Portal")
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
                st.error("Invalid authentication credentials.")

    with mode[1]:
        new_user = st.text_input("New Username")
        new_pass = st.text_input("New Password", type="password")
        if st.button("Register"):
            is_strong, msg = validate_password_strength(new_pass)
            if not is_strong:
                st.warning(msg)
            else:
                try:
                    register_user(new_user, new_pass)
                    st.success("Account verified. Please log in.")
                except sqlite3.IntegrityError:
                    st.error("Identity already exists.")
    st.stop()

# --- Dashboard Screen (Post-Authentication) ---

st.title(f"💼 Financial Control Panel | {st.session_state.current_user}")

with st.sidebar:
    st.header("Transaction Console")
    entry_type = st.selectbox("Entry Type", ["Expense", "Income"])
    categories = ["Food", "Housing", "Transport", "Income/Salary", "Health", "Shopping", "Leisure", "Utility"]
    cat = st.selectbox("Classification", categories)
    amt = st.number_input("Value (ETB)", min_value=1.0, step=50.0)
    note = st.text_input("Memo/Description")
    
    if st.button("Commit Transaction"):
        add_entry(cat, note, amt, entry_type, st.session_state.current_user)
        st.toast("Record Synchronized")
        st.rerun()
    
    st.divider()
    budget = st.number_input("Monthly Target (ETB)", value=10000.0)
    
    if st.button("Terminate Session"):
        st.session_state.authenticated = False
        st.rerun()

# Data Retrieval and Visualization
df_records = load_user_records(st.session_state.current_user)

if not df_records.empty:
    tab_overview, tab_ledger, tab_ai = st.tabs(["📊 Analytics", "📂 Ledger", "🧠 AI Consultant"])
    
    with tab_overview:
        total_in = df_records[df_records['type'] == 'Income']['amount'].sum()
        total_out = df_records[df_records['type'] == 'Expense']['amount'].sum()
        
        # Budget Analysis
        if total_out > budget:
            st.error(f"⚠️ Limit Breach: Exceeded by {total_out - budget:,.2f} ETB")
        else:
            st.success(f"✅ Budget Adherence: {budget - total_out:,.2f} ETB remaining")

        metric_cols = st.columns(3)
        metric_cols[0].metric("Gross Income", f"{total_in:,.2f}")
        metric_cols[1].metric("Gross Expenses", f"{total_out:,.2f}")
        metric_cols[2].metric("Net Liquidity", f"{total_in - total_out:,.2f}")

        chart_cols = st.columns(2)
        with chart_cols[0]:
            expense_filter = df_records[df_records['type'] == 'Expense']
            if not expense_filter.empty:
                fig_pie = px.pie(expense_filter, values='amount', names='category', title="Expense Categorization")
                st.plotly_chart(fig_pie, use_container_width=True)
        with chart_cols[1]:
            fig_bar = px.bar(df_records, x='date', y='amount', color='type', barmode='group', title="Financial Trajectory")
            st.plotly_chart(fig_bar, use_container_width=True)

    with tab_ledger:
        st.subheader("Data Management")
        st.download_button("Export to CSV", data=df_records.to_csv(index=False).encode('utf-8'), file_name="statement.csv")
        
        for idx, row in df_records.iterrows():
            row_cols = st.columns([1, 2, 2, 2, 1])
            row_cols[0].write(row['date'])
            row_cols[1].write(row['category'])
            row_cols[2].write(f"{row['amount']:,.2f}")
            row_cols[3].write(row['type'])
            if row_cols[4].button("Delete", key=f"rm_{row['id']}"):
                remove_entry(row['id'])
                st.rerun()

    with tab_ai:
        st.subheader("Automated Financial Insights")
        if st.button("Generate Expert Report"):
            with st.spinner("AI Engine Analyzing Patterns..."):
                consultant_advice = fetch_ai_analysis(df_records)
                st.markdown(consultant_advice)
else:
    st.info("System Ready. Please input data via the side console to generate insights.")