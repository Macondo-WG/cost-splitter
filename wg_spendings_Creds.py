# %%
import streamlit as st
import bcrypt

# Load user credentials from secrets
users = st.secrets["credentials"]["users"]

# Create a dictionary from usernames to (name, hashed_pw)
user_dict = {u["username"]: (u["name"], u["password_hash"]) for u in users}

# Login form
st.title("🔐 Secure Household Cost Tracker")
username = st.text_input("Username")
password = st.text_input("Password", type="password")

if username in user_dict:
    name, hashed_pw = user_dict[username]
    if bcrypt.checkpw(password.encode(), hashed_pw.encode()):
        st.success(f"Welcome, {name}!")
        
        # Protected content
        st.header("🏠 Add Household Cost")
        payer = st.text_input("Who paid?")
        amount = st.number_input("Amount", min_value=0.0, format="%.2f")

        if st.button("Submit"):
            st.write(f"Recorded: {payer} paid ${amount:.2f}")
    else:
        st.error("Invalid password.")
elif username:
    st.error("Invalid username.")

