import streamlit as st
import pandas as pd
from db import get_connection

# =========================
# Control de acceso
# =========================
usuario = st.session_state.get("usuario")

if not usuario:
    st.warning("Debe iniciar sesión")
    st.stop()

if usuario["perfil"] != 1 or usuario["puesto"].lower() != "coordinador":
    st.error("Acceso restringido a RRHH")
    st.stop()

st.title("👥 RRHH – Gestión de Personal")

conn = get_connection()

# =========================
# Cargar personal
# =========================
df_personal = pd.read_sql("""
    SELECT
        id,
        cedula,
        nombre_completo,
        puesto,
        perfil,
        horario,
        estado,
        fecha_vinculacion,
        fecha_desvinculacion
    FROM personal
    ORDER BY nombre_completo
""", conn)

st.subheader("📋 Personal existente")
st.info("Edite los valores directamente en la tabla y luego presione **Guardar cambi**

