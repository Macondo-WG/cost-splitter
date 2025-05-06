import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Google auth setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
client = gspread.authorize(creds)

# Connect to Google Sheet
sheet = client.open("PermanentExpenses").sheet1

st.title("🏠 Household Cost Tracker")

# Input fields
name = st.selectbox("Name", ["Alice", "Bob", "Carol", "Dave"])
item = st.text_input("Item")
amount = st.number_input("Amount (€)", min_value=0.0, format="%.2f")
date = st.date_input("Date", value=datetime.today())
split_among = st.multiselect('Split among', ["Alice", "Bob", "Carol", "Dave"]))

if st.button("Submit Expense"):
    if name and item and amount:
        sheet.append_row([name, item, amount, date.strftime("%Y-%m-%d"), split_among])
        st.success("💾 Cost saved to Google Sheets!")

# Optionally show existing entries
if st.checkbox("Show existing entries"):
    records = sheet.get_all_records()
    st.write(records)
