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
st.info("Edite los valores directamente en la tabla y luego presione **Guardar cambios**")

# =========================
# Tabla editable
# =========================
df_editado = st.data_editor(
    df_personal,
    use_container_width=True,
    num_rows="fixed",
    disabled=["id", "fecha_vinculacion"]  # PK y fecha histórica
)

# =========================
# Guardar cambios
# =========================
if st.button("💾 Guardar cambios"):
    cur = conn.cursor()

    for _, row in df_editado.iterrows():
        cur.execute("""
            UPDATE personal SET
                cedula = %s,
                nombre_completo = %s,
                puesto = %s,
                perfil = %s,
                horario = %s,
                estado = %s,
                fecha_desvinculacion = %s
            WHERE id = %s
        """, (
            row["cedula"],
            row["nombre_completo"],
            row["puesto"],
            int(row["perfil"]),
            row["horario"],
            row["estado"],
            row["fecha_desvinculacion"],
            int(row["id"])
        ))

    conn.commit()
    st.success("Cambios guardados correctamente")
    st.rerun()

# =========================
# NUEVO INGRESO
# =========================
st.divider()
st.subheader("➕ Crear nuevo personal")

with st.form("nuevo_personal"):
    cedula_n = st.text_input("Cédula")
    nombre_n = st.text_input("Nombre completo")
    password_n = st.text_input("Contraseña", type="password")
    puesto_n = st.text_input("Puesto")
    perfil_n = st.number_input("Perfil (1=Admin, 2=Operador, 3=Supervisor)", min_value=1, max_value=3, step=1)
    horario_n = st.text_input("Horario")
    estado_n = st.selectbox("Estado", ["activo", "inactivo"])
    fecha_vinc_n = st.date_input("Fecha de vinculación")

    crear = st.form_submit_button("Crear persona")

if crear:
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO personal (
                cedula,
                nombre_completo,
                contraseña,
                puesto,
                perfil,
                horario,
                estado,
                fecha_vinculacion
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            cedula_n,
            nombre_n,
            password_n,
            puesto_n,
            int(perfil_n),
            horario_n,
            estado_n,
            fecha_vinc_n
        ))
        conn.commit()
        st.success("Personal creado correctamente")
        st.rerun()
    except Exception as e:
        conn.rollback()
        st.error(f"Error al crear personal: {e}")
