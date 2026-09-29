
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# Page Setup
st.set_page_config(page_title="Library System", layout="wide")
st.title("📚 Advanced Library Management System")

# Function to render tables safely without PyArrow on Windows 7
def show_table(df):
    if df.empty:
        st.info("No records found.")
    else:
        st.write(df.to_html(index=False, escape=False), unsafe_allow_html=True)

# ---------------------------------------------------------
# DATA PERSISTENCE (CSV SAVING & LOADING)
# ---------------------------------------------------------
BOOKS_FILE = "books.csv"
ISSUES_FILE = "issued_records.csv"
FINES_FILE = "fines.csv"

def load_data():
    if os.path.exists(BOOKS_FILE):
        books_df = pd.read_csv(BOOKS_FILE)
    else:
        books_df = pd.DataFrame([
            {"Book ID": 101, "Title": "Python Programming", "Author": "Guido van Rossum", "Category": "IT", "Status": "Available", "Reserved By": "-"},
            {"Book ID": 102, "Title": "Data Science Fundamentals", "Author": "Jake VanderPlas", "Category": "CS", "Status": "Issued", "Reserved By": "-"},
            {"Book ID": 103, "Title": "Database System Concepts", "Author": "Silberschatz", "Category": "IT", "Status": "Available", "Reserved By": "-"},
            {"Book ID": 104, "Title": "Operating Systems", "Author": "Galvin", "Category": "CS", "Status": "Available", "Reserved By": "-"}
        ])
        books_df.to_csv(BOOKS_FILE, index=False)

    if os.path.exists(ISSUES_FILE):
        issues_df = pd.read_csv(ISSUES_FILE)
    else:
        past_due_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        issues_df = pd.DataFrame([
            {"Book ID": 102, "Student Name": "Rahul Sharma", "Issue Date": "2026-08-01", "Due Date": past_due_date, "Status": "Issued"}
        ])
        issues_df.to_csv(ISSUES_FILE, index=False)

    if os.path.exists(FINES_FILE):
        fines_df = pd.read_csv(FINES_FILE)
    else:
        fines_df = pd.DataFrame(columns=["Transaction ID", "Student Name", "Book ID", "Overdue Days", "Fine Amount (Rs)", "Status"])
        fines_df.to_csv(FINES_FILE, index=False)

    return books_df, issues_df, fines_df

def save_data():
    st.session_state.books.to_csv(BOOKS_FILE, index=False)
    st.session_state.issued_records.to_csv(ISSUES_FILE, index=False)
    st.session_state.fines.to_csv(FINES_FILE, index=False)

# Load data into session state
if 'books' not in st.session_state:
    st.session_state.books, st.session_state.issued_records, st.session_state.fines = load_data()

# ---------------------------------------------------------
# NAVIGATION & LOGIN ROLE SELECTOR
# ---------------------------------------------------------
st.sidebar.title("🔐 User Portal")
role = st.sidebar.selectbox("Select Role / Portal", ["Student Portal", "Librarian Dashboard"])

# =========================================================
# STUDENT PORTAL
# =========================================================
if role == "Student Portal":
    st.sidebar.subheader("Student Login")
    student_name = st.sidebar.text_input("Enter Student Name", value="Rahul Sharma")
    
    if student_name:
        st.success(f"Logged in as: **{student_name}**")
        student_menu = st.tabs(["🔍 Search Books", "📌 Reserve Book", "📥 Return Book & Pay Fine", "💳 My Fine Receipts"])
        
        # 1. Search Books
        with student_menu[0]:
            st.header("Search Book Catalog")
            search_query = st.text_input("Search by Title, Author, or Category:")
            filtered_df = st.session_state.books
            if search_query:
                filtered_df = st.session_state.books[
                    st.session_state.books['Title'].astype(str).str.contains(search_query, case=False, na=False) |
                    st.session_state.books['Author'].astype(str).str.contains(search_query, case=False, na=False) |
                    st.session_state.books['Category'].astype(str).str.contains(search_query, case=False, na=False)
                ]
            show_table(filtered_df)

        # 2. Reserve Book
        with student_menu[1]:
            st.header("Reserve a Book")
            available_books = st.session_state.books[st.session_state.books['Status'] == 'Available']
            if available_books.empty:
                st.info("No books are currently available for reservation.")
            else:
                book_to_reserve = st.selectbox("Select Available Book", available_books['Title'].tolist())
                if st.button("Reserve Now"):
                    idx = st.session_state.books[st.session_state.books['Title'] == book_to_reserve].index[0]
                    st.session_state.books.at[idx, 'Reserved By'] = student_name
                    save_data()
                    st.success(f"Book '{book_to_reserve}' has been reserved for {student_name}!")

        # 3. Return Book & Fine Calculation
        with student_menu[2]:
            st.header("Return Issued Books")
            user_issued = st.session_state.issued_records[
                (st.session_state.issued_records['Student Name'].astype(str).str.casefold() == student_name.casefold()) &
                (st.session_state.issued_records['Status'] == 'Issued')
            ]
            
            if user_issued.empty:
                st.info("You have no active issued books.")
            else:
                st.write("### Your Currently Issued Books")
                show_table(user_issued)
                selected_book_id = st.selectbox("Select Book ID to Return", user_issued['Book ID'].tolist())
                
                if st.button("Calculate Fine & Return"):
                    rec_idx = user_issued[user_issued['Book ID'] == selected_book_id].index[0]
                    due_date_str = str(user_issued.loc[rec_idx, 'Due Date'])
                    due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
                    today = datetime.now()
                    
                    overdue_days = (today - due_date).days
                    fine_amount = 0
                    if overdue_days > 0:
                        fine_amount = overdue_days * 10
                        st.warning(f"⚠️ Book is overdue by {overdue_days} days. Fine calculated: Rs. {fine_amount}")
                    else:
                        st.success("✅ Book returned on time! No fine charged.")

                    st.session_state.issued_records.at[rec_idx, 'Status'] = 'Returned'
                    book_idx = st.session_state.books[st.session_state.books['Book ID'] == selected_book_id].index[0]
                    st.session_state.books.at[book_idx, 'Status'] = 'Available'
                    
                    if fine_amount > 0:
                        tx_id = f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}"
                        new_fine = {
                            "Transaction ID": tx_id,
                            "Student Name": student_name,
                            "Book ID": selected_book_id,
                            "Overdue Days": overdue_days,
                            "Fine Amount (Rs)": fine_amount,
                            "Status": "Pending"
                        }
                        st.session_state.fines = pd.concat([st.session_state.fines, pd.DataFrame([new_fine])], ignore_index=True)
                    
                    save_data()
                    st.success(f"Book ID {selected_book_id} returned successfully!")

        # 4. FINE PAYMENT & RECEIPT GENERATION
        with student_menu[3]:
            st.header("💳 Pay Pending Fines")
            pending_fines = st.session_state.fines[
                (st.session_state.fines['Student Name'].astype(str).str.casefold() == student_name.casefold()) &
                (st.session_state.fines['Status'] == 'Pending')
            ]
            
            if pending_fines.empty:
                st.info("You have no pending fines.")
            else:
                show_table(pending_fines)
                pay_tx_id = st.selectbox("Select Transaction ID to Pay", pending_fines['Transaction ID'].tolist())
                
                if st.button("Pay Fine Now"):
                    f_idx = st.session_state.fines[st.session_state.fines['Transaction ID'] == pay_tx_id].index[0]
                    st.session_state.fines.at[f_idx, 'Status'] = 'Paid'
                    save_data()
                    
                    fine_row = st.session_state.fines.loc[f_idx]
                    st.success("🎉 Payment Successful!")
                    
                    st.write("---")
                    st.subheader("🧾 Payment Receipt")
                    st.write(f"**Transaction ID:** {fine_row['Transaction ID']}")
                    st.write(f"**Student Name:** {fine_row['Student Name']}")
                    st.write(f"**Book ID:** {fine_row['Book ID']}")
                    st.write(f"**Amount Paid:** Rs. {fine_row['Fine Amount (Rs)']}")
                    st.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    st.write(f"**Status:** PAID")
                    st.write("---")

# =========================================================
# LIBRARIAN DASHBOARD & EXPORT REPORTS
# =========================================================
else:
    st.header("📊 Librarian Administration Dashboard")
    dash_tabs = st.tabs(["📚 Inventory Control", "📤 Issue Book", "📈 Reports & Analytics"])
    
    # Inventory Control
    with dash_tabs[0]:
        st.subheader("Add New Book to Inventory")
        with st.form("add_book_form"):
            col1, col2 = st.columns(2)
            new_id = col1.number_input("Book ID", min_value=100, step=1)
            new_title = col1.text_input("Title")
            new_author = col2.text_input("Author")
            new_cat = col2.selectbox("Category", ["IT", "CS", "Electronics", "General"])
            
            if st.form_submit_button("Add Book"):
                if new_id in st.session_state.books['Book ID'].values:
                    st.error("Book ID already exists!")
                else:
                    new_row = {"Book ID": new_id, "Title": new_title, "Author": new_author, "Category": new_cat, "Status": "Available", "Reserved By": "-"}
                    st.session_state.books = pd.concat([st.session_state.books, pd.DataFrame([new_row])], ignore_index=True)
                    save_data()
                    st.success(f"Added '{new_title}' to inventory.")

        st.subheader("Current Master Inventory")
        show_table(st.session_state.books)

    # Issue Book
    with dash_tabs[1]:
        st.subheader("Issue Book to Student")
        available = st.session_state.books[st.session_state.books['Status'] == 'Available']
        
        if available.empty:
            st.warning("No books available to issue.")
        else:
            issue_book_id = st.selectbox("Select Book", available['Book ID'].tolist())
            issue_student = st.text_input("Student Name")
            days_to_issue = st.number_input("Issue Duration (Days)", min_value=1, value=7)
            
            if st.button("Issue Book"):
                if issue_student:
                    issue_date = datetime.now().strftime("%Y-%m-%d")
                    due_date = (datetime.now() + timedelta(days=days_to_issue)).strftime("%Y-%m-%d")
                    
                    new_issue = {
                        "Book ID": issue_book_id,
                        "Student Name": issue_student,
                        "Issue Date": issue_date,
                        "Due Date": due_date,
                        "Status": "Issued"
                    }
                    st.session_state.issued_records = pd.concat([st.session_state.issued_records, pd.DataFrame([new_issue])], ignore_index=True)
                    
                    b_idx = st.session_state.books[st.session_state.books['Book ID'] == issue_book_id].index[0]
                    st.session_state.books.at[b_idx, 'Status'] = 'Issued'
                    st.session_state.books.at[b_idx, 'Reserved By'] = '-'
                    save_data()
                    st.success(f"Book ID {issue_book_id} issued to {issue_student} until {due_date}.")
                else:
                    st.error("Please enter student name.")

    # REPORT GENERATION & CSV EXPORT
    with dash_tabs[2]:
        st.subheader("Summary Metrics")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Books", len(st.session_state.books))
        m2.metric("Books Issued", len(st.session_state.books[st.session_state.books['Status'] == 'Issued']))
        m3.metric("Books Available", len(st.session_state.books[st.session_state.books['Status'] == 'Available']))
        
        paid_fines = st.session_state.fines[st.session_state.fines['Status'] == 'Paid']['Fine Amount (Rs)'].sum() if not st.session_state.fines.empty else 0
        m4.metric("Total Fines Collected", f"Rs. {paid_fines}")
        
        st.write("---")
        st.subheader("📋 Issue History Report")
        show_table(st.session_state.issued_records)
        
        st.subheader("💰 Fines Audit Report")
        show_table(st.session_state.fines)
        
        st.write("---")
        st.subheader("📥 Export Reports")
        
        csv_records = st.session_state.issued_records.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📄 Download Issue History (CSV)",
            data=csv_records,
            file_name="issue_history_report.csv",
            mime="text/csv"
        )
        
        csv_fines = st.session_state.fines.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="💰 Download Fines Report (CSV)",
            data=csv_fines,
            file_name="fines_audit_report.csv",
            mime="text/csv"
        )