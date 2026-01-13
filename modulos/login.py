import streamlit as st
from auth import login_usuario

def render():
    st.image("logo.png", width=60)
    st.title("Ingreso al sistema")

    cedula = st.text_input("Cédula")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        login_usuario(cedula, password)
