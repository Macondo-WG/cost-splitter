
import streamlit as st
import bcrypt
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import numpy as np
from datetime import datetime



# Load user credentials from secrets
users = st.secrets["credentials"]["users"]

# Create a dictionary from usernames to (name, hashed_pw)
user_dict = {u["username"]: (u["name"], u["password_hash"]) for u in users}

##### Login form
st.title("🔐 Secure Permanent Expenses Tracker")
username = st.text_input("Username")
password = st.text_input("Password", type="password")

if username in user_dict: # check authentication
    name, hashed_pw = user_dict[username]
    if bcrypt.checkpw(password.encode(), hashed_pw.encode()):
        st.success(f"Welcome, {name}!")
        
         # Google auth setup
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        client = gspread.authorize(creds)

        # Connect to google sheet and get data as a DataFrame
        spreadsheet = client.open("PermanentExpenses")

        worksheet1 = spreadsheet.get_worksheet(0) 
        # Read all values
        values = worksheet1.get_all_values()
        # Check for only headers or full data
        if len(values) > 1:
            df_itemdata = pd.DataFrame(values[1:], columns=values[0])
        else:
            # Only headers are present
            df_itemdata = pd.DataFrame(columns=values[0])


        worksheet2 = spreadsheet.get_worksheet(1) 
        #cumsum = worksheet2.get_all_records() # was not stable
        #df_cumsum = pd.DataFrame(cumsum) 
        # use different method
        values_c = worksheet2.get_all_values()
        # Check for only headers or full data
        if len(values_c) > 1:
            df_cumsum = pd.DataFrame(values_c[1:], columns=values_c[0])
        else:
            # Only headers are present
            df_cumsum = pd.DataFrame(columns=values_c[0])
        list_current_names = df_cumsum.name.to_list() 
        


        #### DEFINE FUNCTION TO CALCULATE LOSS IN VALUE OF EXPENSES OVER YEARS  
        def get_final_investments(df_itemdata, df_cumsum, name):
            '''selects all items in which <name> participated. counts years from day of purchase until day of moving out. 
            calculates negative compund interest with a value decrease of 10% p.a.'''
            
            mask = [name in i for i in df_itemdata.split_among.tolist()]
            no_members = 3 # assume number of WG members stays same
            
            moving_out_date = df_cumsum.loc[df_cumsum['name'] == name, 'moving_out_date'].iloc[0]
            st.write('moving_out_date' , moving_out_date) #debug

            if moving_out_date is not '0':

                years = [round(i.days/365, 2) for i in moving_out_date - df_itemdata.date_of_purchase[mask]]
            
                rest_value_item = df_itemdata.cost[mask] * np.power(np.ones_like(df_itemdata.cost[mask])*(1 - 0.01), years)/no_members

                rest_value_sum = rest_value_item.sum()

                
                return rest_value_sum, rest_value_item
            else:
                return 0,0

        ### button to reset form
        #def on_click(inputs):
        #    for input in inputs:
        #        st.session_state[str(input)] = ""
        #    st.session_state["item"] = ""
        #    st.session_state["cost"] = ""
        #    st.session_state["date_of_purchase"] = "" 
        #    st.session_state["bought_by"] = ""
        #    st.session_state["split_among"] = ""
        #    st.session_state["name"] = ""
        #    st.session_state["mov_in"] = ""
        #    st.session_state["replaces"] = ""    


        ###### CREATE NEW PURCHASE ENTRIES

        st.markdown("""
        ### Create New Purchase Entries
                    """)
        item = st.text_input("Item", key="item")
        cost = st.number_input("Cost (€)", format="%.2f", key="cost")
        date_of_purchase = st.date_input("Date of Purchase", value=datetime.today(), key="date_of_purchase")
        bought_by = st.selectbox("Bought By", list_current_names, key="bought_by")
        split_among = st.multiselect('Split Among', list_current_names, key="split_among")
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
            st.balloons()
           
                      

        # Optionally show table
        if st.checkbox("Show all entries"):
            st.dataframe(df_itemdata)
            
        

        ##### CREATE NEW USER
        st.markdown("""
        ### Create New User
                    """)
        if "show_new_user_form" not in st.session_state:
            st.session_state.show_new_user_form = False

        if st.button('New Member'):
            st.session_state.show_new_user_form = True

        if st.session_state.show_new_user_form:
            name = st.text_input("Name New Member", key="name")
            mov_in = st.date_input("Date of Moving In", key="mov_in")  # Default None removed
            replaces = st.selectbox("Previous Member", list_current_names + [None, 'Add Previous Member Manually'], key="replaces")

            # Create text input for user entry
            if replaces == "Add Previous Member Manually": 
                replaces = st.text_input("Enter New Member", key="replaces_manual")

            # Continue logic if fields are filled
            if name and mov_in and replaces:
                owes, _ = get_final_investments(df_itemdata, df_cumsum, replaces)
                mov_out = 0
                recieves = 0


            if st.button("Add Member to List"):
                new_row = {
                    "name": name,
                    "moving_in_date": mov_in.strftime("%Y-%m-%d"),
                    "owes": owes,
                    "moving_out_date" : mov_out,
                    "recieves": recieves,
                }

                #df_cumsum.loc[len(df_cumsum)] = [name, mov_in, owes, mov_out, recieves ]
                df_cumsum = pd.concat([df_cumsum, pd.DataFrame([new_row])], ignore_index=True)

                # Upload back to Google Sheets
                worksheet2.clear()
                worksheet2.update([df_cumsum.columns.values.tolist()] + df_cumsum.values.tolist())
                st.success("✅ Entry saved!")
                st.balloons()

            #if st.button("Clear Entries" ):
            #    on_click(['name', 'mov_in', 'replaces'])
                


        ### When member moves out call
        st.markdown("""
        ### Billing
                    """)
        
        if "user2move_out_form" not in st.session_state:
            st.session_state.user2move_out_form = False

        if st.button('Moves Out'):
            st.session_state.user2move_out_form = True

        if st.session_state.user2move_out_form: 
            name = st.selectbox("Member to Move Out", list_current_names )
            moving_out_date = st.date_input("Date of Moving Out", value=datetime.today(), key="moving_out_date").strftime("%Y-%m-%d"),
            

            # Find row index (add 2 because gspread is 1-indexed and row 1 is header)
            row_index = df_cumsum[df_cumsum['name'] == name].index[0] + 2
            # Get column indices (also 1-indexed)
            headers = df_cumsum.columns.tolist()
            col_out = headers.index("moving_out_date") + 1
            # Update cells directly
            worksheet2.update_cell(row_index, col_out, moving_out_date)
                      
            recieves, _ = get_final_investments(df_itemdata, df_cumsum, name)
            col_recv = headers.index("recieves") + 1
            worksheet2.update_cell(row_index, col_recv, recieves)

            st.success(f"✅ {name} moves-out date and receives {recieves}.")
        
        #if st.button("Clear Entries"):
        #    for key in ["name"]:
        #        st.session_state.key = ""
        #    st.experimental_rerun()


        if st.button("Logout"):
            st.logout()        

    else:
        st.error("Invalid password.")
elif username:
    st.error("Invalid username.")
    
