import streamlit as st
from permisos import validar_acceso

# =========================
# Control de acceso
# =========================
validar_acceso("Cerrar_Sesion")

# =========================
# Configuración de página
# =========================
st.set_page_config(
    page_title="Cerrar Sesión",
    page_icon="🚪",
    layout="centered"
)

st.image("logo.png", use_container_width=True)

st.title("Sesión cerrada satisfactoriamente")

# =========================
# Cerrar conexión a BD si existe
# =========================
conn = st.session_state.get("conn")
if conn:
    try:
        conn.close()
    except:
        pass

# =========================
# Limpiar sesión
# =========================
st.session_state.clear()

st.success("Su sesión ha sido cerrada correctamente")
st.info("Para volver a acceder, inicie sesión nuevamente")

st.markdown("Puede cerrar esta pestaña o regresar al login.")
