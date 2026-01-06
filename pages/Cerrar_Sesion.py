import streamlit as st

st.set_page_config(
    page_title="Sesión Cerrada Satisfactoriamente",
    page_icon="🚪",
    layout="centered"
)

st.title("🚪 Cerrar sesión")

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

st.info("Para volver a acceder, inicie sesión nuevamente.")

st.markdown("Puede cerrar esta pestaña o regresar al login.")
