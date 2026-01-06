import streamlit as st
import pandas as pd
import psycopg2
from db import get_connection

# =========================
# GUARDIA DE ACCESO
# =========================
usuario = st.session_state.get("usuario")

if not usuario:
    st.warning("Debe iniciar sesión")
    st.stop()

perfil = usuario["perfil"]
puesto = usuario["puesto"]
cedula = usuario["cedula"]

if perfil != 1 or puesto.lower() != "coordinador":
    st.error("Acceso restringido a RRHH")
    st.stop()

st.title("👥 Gestión de Personal (RRHH)")

conn = get_connection()
cur = conn.cursor()

# =========================
# LISTADO DE PERSONAL
# =========================
df_personal = pd.read_sql("""
    SELECT
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
st.dataframe(df_personal, use_container_width=True)

# =========================
# SELECCIÓN PARA EDICIÓN
# =========================
st.subheader("✏️ Editar personal")

cedula_sel = st.selectbox(
    "Seleccione una persona",
    [""] + df_personal["cedula"].tolist()
)

if cedula_sel:
    persona = df_personal[df_personal["cedula"] == cedula_sel].iloc[0]

    with st.form("form_editar"):
        nombre = st.text_input("Nombre completo", persona["nombre_completo"])
        puesto = st.selectbox(
            "Puesto",
            ["Operador", "Supervisor", "Coordinador"],
            index=["Operador", "Supervisor", "Coordinador"].index(persona["puesto"])
        )
        perfil = st.selectbox(
            "Perfil",
            [1, 2, 3],
            index=[1, 2, 3].index(persona["perfil"])
        )
        estado = st.selectbox(
            "Estado",
            ["activo", "inactivo"],
            index=["activo", "inactivo"].index(persona["estado"])
        )
        fecha_vinc = st.date_input("Fecha vinculación", persona["fecha_vinculacion"])
        fecha_desv = st.date_input(
            "Fecha desvinculación",
            persona["fecha_desvinculacion"]
        ) if persona["fecha_desvinculacion"] else st.date_input(
            "Fecha desvinculación", None
        )

        submit = st.form_submit_button("💾 Guardar cambios")

    if submit:
        cur.execute("""
            UPDATE personal SET
                nombre_completo = %s,
                puesto = %s,
                perfil = %s,
                horario = %s,
                estado = %s,
                fecha_vinculacion = %s,
                fecha_desvinculacion = %s
            WHERE cedula = %s
        """, (
            nombre, puesto, perfil, horario, estado,
            fecha_vinc, fecha_desv, cedula_sel
        ))
        conn.commit()
        st.success("Cambios guardados correctamente")
        st.rerun()

# =========================
# NUEVO INGRESO
# =========================
st.subheader("➕ Crear nuevo personal")

with st.form("form_nuevo"):
    cedula_n = st.text_input("Cédula")
    nombre_n = st.text_input("Nombre completo")
    password_n = st.text_input("Contraseña", type="password")
    puesto_n = st.selectbox("Puesto", ["Operador", "Supervisor", "Coordinador"])
    horario_n = st.text_input("Horario")
    perfil_n = st.selectbox("Perfil", [1, 2, 3])
    estado_n = st.selectbox("Estado", ["activo", "inactivo"])
    fecha_vinc_n = st.date_input("Fecha vinculación")

    crear = st.form_submit_button("Crear persona")

if crear:
    try:
        cur.execute("""
            INSERT INTO personal (
                cedula, nombre_completo, contraseña, puesto,
                perfil, estado, fecha_vinculacion
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            cedula_n, nombre_n, password_n,
            puesto_n, perfil_n, horario_n, estado_n, fecha_vinc_n
        ))
        conn.commit()
        st.success("Personal creado correctamente")
        st.rerun()
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        st.error("La cédula ya existe")
