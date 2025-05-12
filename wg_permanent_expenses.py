
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
        spreadsheet = client.open("Permanent_Expenses")

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
        
        worksheet3 = spreadsheet.get_worksheet(2)

        #### DEFINE FUNCTION TO CALCULATE LOSS IN VALUE OF EXPENSES OVER YEARS  
        def get_final_investments(df_itemdata, df_cumsum, name, moving_out_date=None):
            '''selects all items in which <name> participated. counts years from day of purchase until day of moving out. 
            calculates negative compund interest with a value decrease of 10% p.a.'''
            
            mask = [name in i for i in df_itemdata.split_among.tolist()]
            no_members = 3 # assume number of WG members stays same
            
            if moving_out_date is not None: # passed as argument during billing
                st.write('Debug info: roger roger: recieved moving_out_date')
                moving_out_date = moving_out_date
            elif name in df_cumsum['name'].to_list(): # if previous tenant in list, then one can owe
                st.write("Debug info: roger roger: previous tenant's name in list")
                moving_out_date = df_cumsum.loc[df_cumsum['name'] == name, 'moving_out_date'].iloc[0]
            elif name not in df_cumsum['name'].to_list(): # if no previous tenant, one does not owe anything
                st.write('Debug info: no previous tenant')
                moving_out_date = '0'

            if moving_out_date is not '0':

                #time_diffs = pd.to_datetime(moving_out_date, format="%Y-%m-%d")  -  pd.to_datetime(df_itemdata.date_of_purchase[mask], format="%Y-%m-%d")
                #fomrat to pd.datetimearray
                moving_out_date = pd.to_datetime(moving_out_date, format="%Y-%m-%d") 
                time_diffs = moving_out_date-  pd.to_datetime(df_itemdata.date_of_purchase[mask], format="%Y-%m-%d")
                years = [round(i.days/365, 2) for i in time_diffs]
                costs = pd.to_numeric(df_itemdata.cost[mask], errors='coerce')
                
                rest_value_item = round(costs * np.power(np.ones(len(costs))*(1 - 0.1), years)/no_members, 2)
                #st.write('rest value items', type(rest_value_item), rest_value_item)

                ### add inherited expenses but subtract loss of value
                inherited = pd.to_numeric(df_cumsum.loc[df_cumsum['name'] == name, 'owes'].iloc[0], errors='coerce')
                #st.write('inherited', inherited.dtype, inherited)
                
                moving_in_date = df_cumsum.loc[df_cumsum['name'] == name, 'moving_in_date'].iloc[0]
                # format t pd.datetimearray
                moving_in_date = pd.to_datetime(moving_in_date, format="%Y-%m-%d")
                years_in_wg = round((moving_out_date - moving_in_date).days/365, 2)
                rest_of_inherited = inherited * (1-0.1)**years_in_wg
                #st.write(type(rest_of_inherited), rest_of_inherited)
                
                rest_value_sum = rest_value_item.sum() + rest_of_inherited
                
                descrp = ['inherited from previous tenant']
                item_indices = df_itemdata.loc[mask, 'index'].tolist()
                for idx in item_indices:
                    descrp.append(f'share in purchased item {idx}')
                descrp.append('sum')


                costs_to_print = round(costs/3, 2).to_list()
                rest_value_item_to_print = rest_value_item.to_list()
                detailed_list = {'expense': descrp, 
                                 'initial expenses': costs_to_print ,
                                 'rest after value loss': rest_value_item_to_print}
                
                detailed_list['initial expenses'].insert(0, inherited)
                detailed_list['initial expenses'].append(sum(detailed_list['initial expenses']))

                #st.write(len( detailed_list['initial expenses']), detailed_list['initial expenses'])
                detailed_list['rest after value loss'].insert(0, rest_of_inherited)
                detailed_list['rest after value loss'].append(sum(detailed_list['rest after value loss']))
                #st.write(len( detailed_list['rest after value loss']), detailed_list['rest after value loss'])

                return str(round(rest_value_sum, 2)),  pd.DataFrame(detailed_list)
            else:
                return '0','0'




        def append_tenant_bill(worksheet, df_bills, tenant_name=None):
            '''function to print a summary bill of tenant to move out on the third worksheet'''
            # row separator
            worksheet.append_row(["===================================================================="])
            
            if tenant_name:
                worksheet.append_row([f"--- {tenant_name}'s Bill ---"])
            # add headers
            worksheet.append_row(df_bills.columns.tolist())
            # add data
            for row in df_bills.values.tolist():
                worksheet.append_row(row)
            # confirm print    
            st.success("✅ A copy of the bill has been attached to worksheet3 of the associated google sheet")

            


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
                "cost": str(cost),
                "date_of_purchase": date_of_purchase.strftime("%Y-%m-%d"),
                "bought_by": bought_by,
                "split_among" : split_among
            }
            df_itemdata = pd.concat([df_itemdata, pd.DataFrame([new_row])], ignore_index=True)
            #df_itemdata.insert(0, 'index', range(1, len(df_itemdata) + 1))
            df_itemdata.index  = range(1, len(df_itemdata) + 1)

            # Upload back to Google Sheets
            worksheet1.clear()
            worksheet1.update([df_itemdata.columns.values.tolist()] + df_itemdata.values.tolist())
            
            st.success("✅ Entry saved!")
            st.balloons()
           
                      

        # Optionally show table
        if st.checkbox("Show all entries"):
            st.dataframe(df_itemdata)
            
        

        ##### CREATE NEW MEMBER
        st.markdown("""
        ### Create New Member
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

           
            if st.button("Add Member to List"):
                 # Continue logic if fields are filled
                if name and mov_in and replaces:
                    owes, _ = get_final_investments(df_itemdata, df_cumsum, str(replaces))
                    mov_out = 0
                    recieves = 0

                    new_row = {
                        "name": name,
                        "moving_in_date": mov_in.strftime("%Y-%m-%d"),
                        "owes": str(owes),
                        "moving_out_date" : str(mov_out),
                        "recieves": str(recieves),
                    }

                    #df_cumsum.loc[len(df_cumsum)] = [name, mov_in, owes, mov_out, recieves ]
                    df_cumsum = pd.concat([df_cumsum, pd.DataFrame([new_row])], ignore_index=True)

                    # Upload back to Google Sheets
                    worksheet2.clear()
                    worksheet2.update([df_cumsum.columns.values.tolist()] + df_cumsum.values.tolist())
                    st.success(f"✅ {name} was registered and has an open payment to {replaces} of {owes} € !")
                    st.balloons()

                    

            #if st.button("Clear Entries" ):
            #    on_click(['name', 'mov_in', 'replaces'])
                


        ### When member moves out call
        st.markdown("""
        ### Billing
                    """)
        
        if "user2move_out_form" not in st.session_state:
            st.session_state.user2move_out_form = False

        if st.button('Open Form for Member to Move Out'):
            st.session_state.user2move_out_form = True

        if st.session_state.user2move_out_form: 
            name = st.selectbox("Member to Move Out", list_current_names )
            moving_out_date = st.date_input("Date of Moving Out", value=datetime.today(), key="moving_out_date")
            moving_out_date_str = "'" + moving_out_date.strftime("%Y-%m-%d")
            
            if st.button("Bill"):
                # Find row index (add 2 because gspread is 1-indexed and row 1 is header)
                row_index = df_cumsum[df_cumsum['name'] == name].index[0] + 2
                # Get column indices (also 1-indexed)
                headers = df_cumsum.columns.tolist()
                col_out = headers.index("moving_out_date") + 1
                # Update cells directly
                worksheet2.update_cell(row_index, col_out, moving_out_date_str)

                ###degub 
                #moving_out_date = df_cumsum.loc[df_cumsum['name'] == name, 'moving_out_date'].iloc[0]
                #moving_out_date = pd.to_datetime(moving_out_date, format="%Y-%m-%d") 
                #st.write('moving out date', moving_out_date, type(moving_out_date))
                recieves, detailed_df = get_final_investments(df_itemdata, df_cumsum, name, moving_out_date=moving_out_date)
                col_recv = headers.index("recieves") + 1
                worksheet2.update_cell(row_index, col_recv, str(recieves))
                
                st.success(f"✅ {name} moves-out on {moving_out_date_str} and receives {recieves} €.")
                st.markdown("Detailed list of expenses and loss of value:")
                st.write(detailed_df)
                
                append_tenant_bill(worksheet3, detailed_df, tenant_name=name)
                
                
        if st.button("Logout"):
            st.logout()        

    else:
        st.error("Invalid password.")
elif username:
    st.error("Invalid username.")
    
