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
# Cargar posibles supervisores
# =========================
df_supervisores = pd.read_sql("""
    SELECT nombre_completo
    FROM personal
    WHERE estado = 'activo'
      AND puesto <> 'Operario Catastral'
    ORDER BY nombre_completo
""", conn)

lista_supervisores = [""] + df_supervisores["nombre_completo"].tolist()

# =========================
# Selección de modo
# =========================
modo = st.radio(
    "Seleccione una acción:",
    ["Personal Existente", "Crear Nuevo Personal"]
)

# =====================================================
# MODO: PERSONAL EXISTENTE
# =====================================================
if modo == "Personal Existente":

    df_personal = pd.read_sql("""
        SELECT
            id,
            cedula,
            nombre_completo,
            contraseña,
            puesto,
            perfil,
            horario,
            estado,
            supervisor,
            fecha_vinculacion,
            fecha_desvinculacion
        FROM personal
        ORDER BY nombre_completo
    """, conn)

    st.subheader("📋 Personal existente")
    st.info("Seleccione un empleado para editar sus datos")

    empleado_seleccionado = st.selectbox(
        "Empleado",
        df_personal["nombre_completo"]
    )

    df_empleado = df_personal[
        df_personal["nombre_completo"] == empleado_seleccionado
    ].iloc[0]

    # Índice del supervisor actual
    sup_actual = df_empleado["supervisor"] if pd.notnull(df_empleado["supervisor"]) else ""
    idx_sup = lista_supervisores.index(sup_actual) if sup_actual in lista_supervisores else 0

    with st.form("editar_personal"):
        cedula = st.text_input("Cédula", value=df_empleado["cedula"])
        nombre = st.text_input("Nombre completo", value=df_empleado["nombre_completo"])
        contraseña = st.text_input("Contraseña", value=df_empleado["contraseña"])
        puesto = st.text_input("Puesto", value=df_empleado["puesto"])
        perfil = st.number_input(
            "Perfil (1=Admin, 2=Operador, 3=Supervisor)",
            min_value=1,
            max_value=3,
            value=int(df_empleado["perfil"]),
            step=1
        )
        horario = st.text_input("Horario", value=df_empleado["horario"])
        estado = st.selectbox(
            "Estado",
            ["activo", "inactivo"],
            index=0 if df_empleado["estado"] == "activo" else 1
        )

        supervisor = st.selectbox(
            "Supervisor",
            lista_supervisores,
            index=idx_sup
        )

        fecha_desvinc = st.date_input(
            "Fecha de desvinculación",
            value=df_empleado["fecha_desvinculacion"]
            if pd.notnull(df_empleado["fecha_desvinculacion"]) else None
        )

        guardar = st.form_submit_button("💾 Guardar cambios")

    if guardar:
        cur = conn.cursor()
        try:
            cur.execute("""
                UPDATE personal SET
                    cedula = %s,
                    nombre_completo = %s,
                    contraseña = %s,
                    puesto = %s,
                    perfil = %s,
                    horario = %s,
                    estado = %s,
                    supervisor = %s,
                    fecha_desvinculacion = %s
                WHERE id = %s
            """, (
                cedula,
                nombre,
                contraseña,
                puesto,
                int(perfil),
                horario,
                estado,
                supervisor if supervisor != "" else None,
                fecha_desvinc,
                int(df_empleado["id"])
            ))
            conn.commit()
            st.success("✅ Cambios guardados correctamente")
        except Exception as e:
            conn.rollback()
            st.error(f"❌ Error al guardar cambios: {e}")

# =====================================================
# MODO: CREAR NUEVO PERSONAL
# =====================================================
elif modo == "Crear Nuevo Personal":

    st.subheader("➕ Crear nuevo personal")

    with st.form("nuevo_personal"):
        cedula_n = st.text_input("Cédula")
        nombre_n = st.text_input("Nombre completo")
        password_n = st.text_input("Contraseña", type="password")
        puesto_n = st.text_input("Puesto")
        perfil_n = st.number_input(
            "Perfil (1=Admin, 2=Operador, 3=Supervisor)",
            min_value=1, max_value=3, step=1
        )
        horario_n = st.text_input("Horario")
        estado_n = st.selectbox("Estado", ["activo", "inactivo"])

        supervisor_n = st.selectbox(
            "Supervisor",
            lista_supervisores
        )

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
                    supervisor,
                    fecha_vinculacion
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                cedula_n,
                nombre_n,
                password_n,
                puesto_n,
                int(perfil_n),
                horario_n,
                estado_n,
                supervisor_n if supervisor_n != "" else None,
                fecha_vinc_n
            ))
            conn.commit()
            st.success("✅ Personal creado correctamente")
        except Exception as e:
            conn.rollback()
            st.error(f"❌ Error al crear personal: {e}")
