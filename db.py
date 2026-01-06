import psycopg2
import streamlit as st
import os

@st.cache_resource
def get_connection():
    return psycopg2.connect(os.environ["DB_URI"])
