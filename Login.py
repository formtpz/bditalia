import streamlit as st
from auth import login_usuario
from permisos import validar_acceso

# =========================
# Configuración de página
# =========================
st.set_page_config(
    page_title="Sistema de Reportes - Login",
    page_icon="🔐",
    layout="centered"
)

# =========================
# Control de acceso
# =========================
# Login siempre está permitido

# =========================
# Vista
# =========================
usuario = st.session_state.get("usuario")

st.image("logo.png", use_container_width=True)

# -------- NO LOGUEADO --------
if not usuario:
    st.title("Ingreso al sistema")

    cedula = st.text_input("Cédula")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        login_usuario(cedula, password)

# -------- YA LOGUEADO --------
else:
    st.title("Acceso correcto")
    st.success(f"Bienvenido {usuario['nombre']}")
    st.info("Use el menú lateral para navegar por el sistema")
