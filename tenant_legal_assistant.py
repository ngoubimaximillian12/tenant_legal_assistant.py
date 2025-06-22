# tenant_legal_assistant.py

import streamlit as st
import pandas as pd
import datetime
import base64
from sqlalchemy import create_engine, Column, Integer, String, Text, Date, MetaData, Table
from fpdf import FPDF
import openai

# -------- Configuration --------
openai.api_key = "your-openai-api-key"

# -------- Database Setup --------
engine = create_engine('sqlite:///tenant_assistant.db')
metadata = MetaData()

# All tables
messages = Table('messages', metadata,
    Column('id', Integer, primary_key=True),
    Column('user_name', String(50)),
    Column('state', String(50)),
    Column('user_message', Text),
    Column('bot_response', Text)
)

leases = Table('leases', metadata,
    Column('id', Integer, primary_key=True),
    Column('user_name', String(50)),
    Column('state', String(50)),
    Column('lease_text', Text),
    Column('analysis', Text)
)

reminders = Table('reminders', metadata,
    Column('id', Integer, primary_key=True),
    Column('user_name', String(50)),
    Column('title', String(100)),
    Column('due_date', Date),
    Column('notes', Text)
)

issues = Table('issues', metadata,
    Column('id', Integer, primary_key=True),
    Column('user_name', String(50)),
    Column('date_reported', Date),
    Column('description', Text),
    Column('urgency', String(20)),
    Column('status', String(20))
)

vault = Table('vault', metadata,
    Column('id', Integer, primary_key=True),
    Column('user_name', String(50)),
    Column('category', String(50)),
    Column('file_name', String(100)),
    Column('upload_date', Date),
    Column('notes', Text)
)

rentlog = Table('rentlog', metadata,
    Column('id', Integer, primary_key=True),
    Column('user_name', String(50)),
    Column('month', String(20)),
    Column('amount', String(20)),
    Column('status', String(20)),
    Column('notes', Text)
)

costs = Table('costs', metadata,
    Column('id', Integer, primary_key=True),
    Column('user_name', String(50)),
    Column('category', String(50)),
    Column('amount', String(20)),
    Column('notes', Text),
    Column('date_logged', Date)
)

metadata.create_all(engine)

# -------- Session & Login --------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username:
            st.session_state.logged_in = True
            st.session_state.user_name = username
        else:
            st.error("Invalid credentials.")
    st.stop()

user_name = st.session_state.user_name
# -------- Navigation --------
tabs = st.tabs([
    "🏠 Dashboard", "💬 Legal Chat", "🧭 What Should I Do?", "📄 Letters", "📅 Calendar",
    "📂 Vault", "🛠️ Tracker", "📍 Legal Aid", "🧾 Rent Log", "🌍 Language",
    "🧑‍💼 Pro Portal", "💰 Cost Summary"
])

# -------- Dashboard --------
with tabs[0]:
    st.title("🏠 Tenant Assistant Dashboard")
    st.success(f"Welcome back, {user_name}!")
    st.markdown("Quick access to your legal tools, reminders, and files.")

# -------- Legal Chat Interactive --------
with tabs[1]:
    st.subheader("💬 Interactive Legal Chat")
    user_state = st.selectbox("Select your state", ["California", "New York", "Texas", "Florida", "Other"])

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for entry in st.session_state.chat_history:
        st.chat_message("user").write(entry["user"])
        st.chat_message("assistant").write(entry["bot"])

    user_input = st.chat_input("Ask your legal question...")
    if user_input:
        prompt = [
            {"role": "system", "content": f"You are a helpful legal assistant specialized in tenant laws in {user_state}. Keep responses clear and concise."}
        ]
        for msg in st.session_state.chat_history:
            prompt.append({"role": "user", "content": msg["user"]})
            prompt.append({"role": "assistant", "content": msg["bot"]})
        prompt.append({"role": "user", "content": user_input})

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=prompt,
                max_tokens=500
            )
            bot_response = response.choices[0].message.content.strip()
        except Exception as e:
            bot_response = f"Error: {e}"

        st.chat_message("user").write(user_input)
        st.chat_message("assistant").write(bot_response)

        st.session_state.chat_history.append({"user": user_input, "bot": bot_response})

    if st.button("💾 Save Chat & Exit"):
        with engine.connect() as conn:
            for msg in st.session_state.chat_history:
                conn.execute(messages.insert().values(
                    user_name=user_name,
                    state=user_state,
                    user_message=msg["user"],
                    bot_response=msg["bot"]
                ))
        st.success("Chat saved. Thank you!")
        st.session_state.chat_history.clear()
# -------- What Should I Do Wizard --------
with tabs[2]:
    st.subheader("🧭 What Should I Do?")
    issue = st.selectbox("Select a common problem:", [
        "Didn't get my security deposit", "Landlord won't repair something",
        "Received eviction notice", "Want to break lease"
    ])
    if issue:
        st.markdown(f"**You selected:** {issue}")
        if issue == "Didn't get my security deposit":
            st.markdown("- 📝 Generate refund request letter\n- 📅 Add reminder\n- 📂 Upload lease and receipts")
        elif issue == "Landlord won't repair something":
            st.markdown("- 🛠️ Log repair\n- 📝 Generate repair request letter\n- 📷 Upload photo evidence")
        elif issue == "Received eviction notice":
            st.markdown("- 📄 Generate response letter\n- 🏛️ Add court date\n- 📍 Search legal aid")
        elif issue == "Want to break lease":
            st.markdown("- 📄 Generate lease termination letter\n- 📅 Set move-out reminder")

# -------- Legal Letter Generator --------
with tabs[3]:
    st.subheader("📄 Generate Legal Letter")
    letter_type = st.selectbox("Letter Type", [
        "Repair Request", "Deposit Refund", "Lease Termination", "Eviction Response"
    ])
    landlord_name = st.text_input("Landlord's Name")
    landlord_address = st.text_area("Landlord's Address")
    tenant_address = st.text_area("Your Address")
    issue_desc = st.text_area("Describe the Issue")

    if st.button("Generate Letter"):
        prompt = f"""
        You are a legal assistant. Write a {letter_type} letter from a tenant in {user_state}.
        Landlord: {landlord_name}
        Address: {landlord_address}
        Tenant Address: {tenant_address}
        Issue: {issue_desc}
        """
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "system", "content": prompt}],
                max_tokens=600
            )
            letter = response.choices[0].message.content.strip()
            st.text_area("📄 Your Letter", value=letter, height=400)

            # PDF download
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            for line in letter.split("\n"):
                pdf.multi_cell(0, 10, line)
            pdf_bytes = pdf.output(dest="S").encode("latin1")
            b64 = base64.b64encode(pdf_bytes).decode()
            st.markdown(f"📥 [Download Letter (PDF)](data:application/pdf;base64,{b64})", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error generating letter: {e}")

# -------- Calendar Tab --------
with tabs[4]:
    st.subheader("📅 Reminders & Deadlines")

    reminder_title = st.text_input("Reminder Title")
    due_date = st.date_input("Due Date")
    reminder_notes = st.text_area("Notes")

    if st.button("Add Reminder"):
        with engine.connect() as conn:
            conn.execute(reminders.insert().values(
                user_name=user_name,
                title=reminder_title,
                due_date=due_date,
                notes=reminder_notes
            ))
        st.success("Reminder saved!")

    st.markdown("### 📆 Upcoming Reminders")
    today = datetime.date.today()
    df = pd.read_sql(f"SELECT * FROM reminders WHERE user_name = '{user_name}' AND due_date >= '{today}'", engine)
    st.dataframe(df)
# -------- Document Vault --------
with tabs[5]:
    st.subheader("📂 Document Vault")
    category = st.selectbox("Category", ["Lease", "Evidence", "Receipts", "Photos", "Other"])
    uploaded_file = st.file_uploader("Upload a file")
    file_notes = st.text_area("File Notes")

    if uploaded_file and st.button("Save Document"):
        with engine.connect() as conn:
            conn.execute(vault.insert().values(
                user_name=user_name,
                category=category,
                file_name=uploaded_file.name,
                upload_date=datetime.date.today(),
                notes=file_notes
            ))
        st.success("File saved to vault!")

    st.markdown("### 📁 My Uploaded Files")
    vault_df = pd.read_sql(f"SELECT * FROM vault WHERE user_name = '{user_name}'", engine)
    st.dataframe(vault_df)

# -------- Issue Tracker --------
with tabs[6]:
    st.subheader("🛠️ Report an Issue")
    issue_text = st.text_area("Describe the issue")
    urgency = st.selectbox("Urgency", ["Low", "Medium", "High"])
    if st.button("Submit Issue"):
        with engine.connect() as conn:
            conn.execute(issues.insert().values(
                user_name=user_name,
                date_reported=datetime.date.today(),
                description=issue_text,
                urgency=urgency,
                status="Open"
            ))
        st.success("Issue reported.")

    st.markdown("### 📋 Logged Issues")
    issue_df = pd.read_sql(f"SELECT * FROM issues WHERE user_name = '{user_name}'", engine)
    st.dataframe(issue_df)

# -------- Legal Aid Finder --------
with tabs[7]:
    st.subheader("📍 Find Local Legal Aid")
    zip_code = st.text_input("Enter your ZIP code")
    if st.button("Search"):
        st.markdown(f"### Legal Aid near ZIP: {zip_code}")
        st.write("• Legal Aid Society\n• Tenant Union Hotline\n• Housing Justice Center")
        st.info("Demo only — replace with real API later.")

# -------- Rent Log --------
with tabs[8]:
    st.subheader("🧾 Rent Log")
    month = st.text_input("Month (e.g., June 2025)")
    rent_amt = st.text_input("Amount ($)")
    status = st.selectbox("Status", ["Paid", "Unpaid", "Partial"])
    rent_notes = st.text_area("Notes")

    if st.button("Log Rent"):
        with engine.connect() as conn:
            conn.execute(rentlog.insert().values(
                user_name=user_name,
                month=month,
                amount=rent_amt,
                status=status,
                notes=rent_notes
            ))
        st.success("Rent recorded.")

    st.markdown("### 💳 Payment History")
    rent_df = pd.read_sql(f"SELECT * FROM rentlog WHERE user_name = '{user_name}'", engine)
    st.dataframe(rent_df)

# -------- Language --------
with tabs[9]:
    st.subheader("🌍 Language Settings")
    lang = st.selectbox("Choose Language", ["English", "Spanish", "Arabic", "French", "Chinese"])
    st.info(f"Language set to: {lang}. Translation engine coming soon.")

# -------- Pro Portal --------
with tabs[10]:
    st.subheader("🧑‍💼 Advocate Portal")
    if user_name.startswith("advocate_"):
        all_msgs = pd.read_sql("SELECT * FROM messages", engine)
        st.dataframe(all_msgs)
    else:
        st.warning("Access denied: only for verified legal advocates.")

# -------- Cost Summary --------
with tabs[11]:
    st.subheader("💰 Financial Summary")
    cost_category = st.selectbox("Cost Type", [
        "Rent Paid", "Deposit Paid", "Late Fee", "Deduction", "Refund", "Other"
    ])
    cost_amt = st.text_input("Amount ($)")
    cost_notes = st.text_area("Notes")
    if st.button("Add Cost Entry"):
        with engine.connect() as conn:
            conn.execute(costs.insert().values(
                user_name=user_name,
                category=cost_category,
                amount=cost_amt,
                notes=cost_notes,
                date_logged=datetime.date.today()
            ))
        st.success("Cost logged.")

    st.markdown("### 📊 All Cost Entries")
    cost_df = pd.read_sql(f"SELECT * FROM costs WHERE user_name = '{user_name}'", engine)
    st.dataframe(cost_df)

    # Calculate summary
    def sum_cat(cat):
        return cost_df[cost_df['category'] == cat]['amount'].astype(float).sum()

    rent_total = sum_cat("Rent Paid")
    deposit_paid = sum_cat("Deposit Paid")
    late_fees = sum_cat("Late Fee")
    deductions = sum_cat("Deduction")
    refunds = sum_cat("Refund")
    est_due = deposit_paid - deductions

    st.markdown("### 💼 Summary")
    st.metric("Total Rent Paid", f"${rent_total:,.2f}")
    st.metric("Deposit Paid", f"${deposit_paid:,.2f}")
    st.metric("Deductions", f"${deductions:,.2f}")
    st.metric("Refunds Received", f"${refunds:,.2f}")
    st.metric("Estimated Refund Owed", f"${est_due:,.2f}")
