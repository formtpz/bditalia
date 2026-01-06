import streamlit as st
from auth import login_usuario

st.set_page_config(page_title="Sistema de Reportes", layout="centered")

st.markdown("""
<style>
/* Texto de los items del menú */
section[data-testid="stSidebar"] nav a {
    font-size: 20px !important;
    font-weight: 600;
}

/* Título "Pages" */
section[data-testid="stSidebar"] h2 {
    font-size: 18px !important;
}
</style>
""", unsafe_allow_html=True)

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.image("logo.png", use_container_width=True)
    st.title("Ingreso al sistema")

    cedula = st.text_input("Cédula")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        login_usuario(cedula, password)
else:
    st.success(f"Bienvenido {st.session_state.nombre}")
    st.info("Use el menú lateral para navegar")
