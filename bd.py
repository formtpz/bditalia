import psycopg2
import streamlit as st

@st.cache_resource
def get_connection():
    return psycopg2.connect(
        host="HOST",
        database="DB",
        user="USER",
        password="PASSWORD"
    )
