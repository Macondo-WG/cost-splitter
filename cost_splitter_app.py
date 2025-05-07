
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
data = worksheet1.get_all_records()
df_itemdata = pd.DataFrame(data)

worksheet2 = spreadsheet.get_worksheet(1) 
cumsum = worksheet2.get_all_records()
df_cumsum = pd.DataFrame(cumsum)
#list_current_names = df_cumsum.name.to_list()
list_current_names = ['Leon', 'Robin', 'Alessia']


if st.button("print cols"):
    print(data)
    print(df_cumsum.columns.tolist())
    df_itemdata.columns.to_list()

    
