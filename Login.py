# --- Streamlit Page ---
# title: Recurso Humano
# icon: 👥

import streamlit as st
from auth import login_usuario

st.set_page_config(page_title="Sistema de Reportes", layout="centered")



# =========================
# LOGIN
# =========================
usuario = st.session_state.get("usuario")

if not usuario:
    st.image("logo.png", use_container_width=True)
    st.title("Ingreso al sistema")

    cedula = st.text_input("Cédula")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        login_usuario(cedula, password)

else:
    st.image("logo.png", use_container_width=True)
    st.title("Acceso Correcto")
    st.success(f"Bienvenido {usuario['nombre']}")
    st.info("Use el menú lateral para navegar")
   


