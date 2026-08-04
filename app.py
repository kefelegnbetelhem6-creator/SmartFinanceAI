import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import requests
import os
import plotly.express as px
from dotenv import load_dotenv

# Configuration
load_dotenv()
st.set_page_config(page_title="Finance AI System", page_icon="📊", layout="wide")

# --- Database Logic ---
def init_db():
    conn = sqlite3.connect('finance_system.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT, category TEXT, description TEXT, amount REAL, type TEXT)''')
    conn.commit()
    conn.close()

def add_transaction(category, description, amount, trans_type):
    conn = sqlite3.connect('finance_system.db')
    c = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d")
    c.execute("INSERT INTO transactions (date, category, description, amount, type) VALUES (?, ?, ?, ?, ?)",
              (date, category, description, amount, trans_type))
    conn.commit()
    conn.close()

def delete_transaction(id):
    conn = sqlite3.connect('finance_system.db')
    c = conn.cursor()
    c.execute("DELETE FROM transactions WHERE id=?", (id,))
    conn.commit()
    conn.close()

def get_data_as_df():
    conn = sqlite3.connect('finance_system.db')
    df = pd.read_sql_query("SELECT * FROM transactions", conn)
    conn.close()
    return df

# --- AI Logic (Groq/Llama 3) ---
# --- AI Logic (Groq/Llama 3) ---
# --- AI Logic (Short & Direct Version) ---
def get_ai_insights(df):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key: return "Error: API Key missing."
    
    summary = df.groupby(['type', 'category'])['amount'].sum().to_dict()
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system", 
                # ትዕዛዙን አሳጥረነዋል - ሰላምታና መደምደሚያ እንዳይጽፍ አዝዘነዋል
                "content": "You are a direct financial expert. Analyze the data and provide ONLY 2-3 short bullet points of advice. No introduction, no conclusion, and no fluff. English only."
            },
            {"role": "user", "content": f"Data: {summary}"}
        ]
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        return response.json()['choices'][0]['message']['content']
    except:
        return "AI Service is unavailable."

# --- Main UI ---
init_db()
st.title("📊 Finance AI System")

# Sidebar - Input Section
with st.sidebar:
    st.header("Transaction Entry")
    t_type = st.selectbox("Type", ["Expense", "Income"])
    cat_options = ["Food", "Rent", "Transport", "Salary", "Health", "Education", "Shopping", "Entertainment", "Other"]
    category = st.selectbox("Category", cat_options)
    amount = st.number_input("Amount (ETB)", min_value=1.0)
    desc = st.text_input("Description")
    
    if st.button("Save Transaction"):
        add_transaction(category, desc, amount, t_type)
        st.success("Record Saved")
        st.rerun()
    
    st.divider()
    st.header("Budget Settings")
    budget_limit = st.number_input("Monthly Budget Limit (ETB)", min_value=0.0, value=10000.0)

# Main Dashboard Tabs
tab1, tab2, tab3 = st.tabs(["📈 Dashboard", "📂 Records", "🤖 AI Insights"])

df = get_data_as_df()

if not df.empty:
    with tab1:
        st.subheader("Financial Overview")
        income = df[df['type'] == 'Income']['amount'].sum()
        expense = df[df['type'] == 'Expense']['amount'].sum()
        net_balance = income - expense
        
        # Budget Alert Logic
        if expense > budget_limit:
            st.error(f"⚠️ Budget Alert: You have exceeded your limit by {expense - budget_limit:,.2f} ETB")
        else:
            st.success(f"✅ Budget Status: You have {budget_limit - expense:,.2f} ETB remaining for the month.")

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Income", f"{income:,.2f} ETB")
        col2.metric("Total Expense", f"{expense:,.2f} ETB")
        col3.metric("Net Balance", f"{net_balance:,.2f} ETB")

        # Visualization
        col_left, col_right = st.columns(2)
        with col_left:
            st.write("Expenses by Category")
            exp_df = df[df['type'] == 'Expense']
            if not exp_df.empty:
                fig_pie = px.pie(exp_df, values='amount', names='category', hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)
        
        with col_right:
            st.write("Transaction Trends")
            fig_bar = px.bar(df, x='date', y='amount', color='type', barmode='group')
            st.plotly_chart(fig_bar, use_container_width=True)

    with tab2:
        st.subheader("Data Management")
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export CSV", data=csv, file_name="finance_records.csv", mime="text/csv")
        
        # Display Records with Delete Option
        for index, row in df.iterrows():
            cols = st.columns([1, 2, 2, 2, 1, 1])
            cols[0].write(row['id'])
            cols[1].write(row['date'])
            cols[2].write(row['category'])
            cols[3].write(row['amount'])
            cols[4].write(row['type'])
            if cols[5].button("🗑️", key=f"del_{row['id']}"):
                delete_transaction(row['id'])
                st.rerun()
        st.divider()

    with tab3:
        st.subheader("AI Financial Analysis")
        if st.button("Generate AI Report"):
            with st.spinner("Processing Data..."):
                advice = get_ai_insights(df)
                st.markdown(advice)

else:
    st.info("No records found. Use the sidebar to add transactions.")