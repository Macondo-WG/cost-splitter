
import streamlit as st
import bcrypt
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import numpy as np
from datetime import datetime




# Google auth setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
client = gspread.authorize(creds)

# Connect to sheet and get data as a DataFrame
spreadsheet = client.open("PermanentExpenses")


worksheet1 = spreadsheet.get_worksheet(0) 
#data = worksheet1.get_all_records()
#df_itemdata = pd.DataFrame(data)
# Read all values
values = worksheet1.get_all_values()
# Check for only headers or full data
if len(values) > 1:
    df_itemdata = pd.DataFrame(values[1:], columns=values[0])
else:
    # Only headers are present
    df_itemdata = pd.DataFrame(columns=values[0])




worksheet2 = spreadsheet.get_worksheet(1) 
#cumsum = worksheet2.get_all_records()
#df_cumsum = pd.DataFrame(cumsum)
# Read all values
values_c = worksheet2.get_all_values()
# Check for only headers or full data
if len(values_c) > 1:
    df_cumsum = pd.DataFrame(values_c[1:], columns=values_c[0])
else:
    # Only headers are present
    df_cumsum = pd.DataFrame(columns=values_c[0])


list_current_names = df_cumsum.name.to_list()
#list_current_names = ['Leon', 'Robin', 'Alessia']


if st.button("print cols"):
    #df_itemdata.columns = df_itemdata.columns.str.strip().str.lower()
    st.write(df_itemdata)
    st.write(df_cumsum)
    



def get_final_investments(df_itemdata, df_cumsum, name):
    '''selects all items in which <name> participated. counts years from day of purchase until day of moving out. 
    calculates negative compund interest with a value decrease of 10% p.a.'''
    no_members = 3 # assume number of WG members stays same
    mask = [name in i for i in df_itemdata.split_among.tolist()]
    
    years = [round(i.days/365, 2) for i in df_cumsum.moving_out_date[mask] - df_itemdata.date_of_purchase[mask]]

    rest_value_item = df_itemdata.cost[mask] * np.power(np.ones_like(df_itemdata.cost[mask])*(1 - 0.01), years)/no_members

    rest_value_sum = rest_value_item.sum()

    return rest_value_sum, rest_value_item
    


###### CREATE NEW PURCHASE ENTRIES
item = st.text_input("Item")
cost = st.number_input("Amount (€)", min_value=0.0, format="%.2f")
date_of_purchase = st.date_input("Date", value=datetime.today())
bought_by = st.selectbox("Name", list_current_names)
split_among = st.multiselect('Split among', list_current_names)
split_among = ", ".join(split_among)

# Add a new row and update the sheet
# headers in sheet: item	cost	date_of_purchase	bought_by	split_among
if st.button("Submit Expense"):
    new_row = {
        "item": item,
        "cost": cost,
        "date_of_purchase": date_of_purchase.strftime("%Y-%m-%d"),
        "bought_by": bought_by,
        "split_among" : split_among
    }
    df_itemdata = pd.concat([df_itemdata, pd.DataFrame([new_row])], ignore_index=True)

    # Upload back to Google Sheets
    worksheet1.clear()
    worksheet1.update([df_itemdata.columns.values.tolist()] + df_itemdata.values.tolist())
    st.success("✅ Entry saved!")

# Optionally show table
if st.checkbox("Show all entries"):
    st.dataframe(df_itemdata)




##### CREATE NEW USER

if "show_new_user_form" not in st.session_state:
    st.session_state.show_new_user_form = False

if st.button('New Member'):
    st.session_state.show_new_user_form = True

if st.session_state.show_new_user_form:
    name = st.text_input("Name New Member")
    mov_in = st.date_input("Date of Moving In")  # Default None removed
    replaces = st.selectbox("Previous Member", list_current_names)
    
    # Continue logic if fields are filled
    if name and mov_in and replaces:
        owes, _ = get_final_investments(df_itemdata, df_cumsum, replaces)
        mov_out = 0
        recieves = 0


if st.button("Add Member to List"):
    new_row = {
        "name": name,
        "moving_in_date": mov_in,
        "owes": owes,
        "moving_out_date" : mov_out,
        "recieves": 0,
    }
    df_cumsum.loc[len(df_cumsum)] = [name, mov_in, owes, mov_out, recieves ]
    #df_itemdata = pd.concat([df_itemdata, pd.DataFrame([new_row])], ignore_index=True)

    # Upload back to Google Sheets
    worksheet2.clear()
    worksheet2.update([df_cumsum.columns.values.tolist()] + df_cumsum.values.tolist())
    st.success("✅ Entry saved!")
