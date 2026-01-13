import streamlit as st
from db import get_connection
from datetime import date

# =========================
# Control de acceso
# =========================
usuario = st.session_state.get("usuario")

if not usuario:
    st.warning("Debe iniciar sesión")
    st.stop()

perfil = usuario["perfil"]
puesto = usuario["puesto"].lower()
cedula_usuario = usuario["cedula"]
nombre_usuario = usuario["nombre"]

# Perfiles permitidos
# 1 = Admin / Coordinador
# 2 = Operador
# 3 = Supervisor
if perfil not in (1, 2, 3):
    st.error("No tiene permiso para acceder a esta sección")
    st.stop()

st.title("📊 Reporte de Producción")

conn = get_connection()
cur = conn.cursor()

# =========================
# Cargar procesos
# =========================
cur.execute("""
    SELECT id, nombre
    FROM procesos
    ORDER BY nombre
""")

procesos = cur.fetchall()

if not procesos:
    st.error("No existen procesos registrados")
    st.stop()

procesos_dict = {nombre: pid for pid, nombre in procesos}

# =========================
# Obtener supervisor REAL desde personal
# (snapshot histórico)
# =========================
cur.execute("""
    SELECT supervisor
    FROM personal
    WHERE cedula = %s
""", (cedula_usuario,))

row_sup = cur.fetchone()
supervisor_nombre = row_sup[0] if row_sup else None

# =========================
# Formulario
# =========================
with st.form("form_reporte_produccion"):
    st.subheader("Datos del reporte")

    fecha_reporte = st.date_input(
        "Fecha del reporte",
        value=date.today()
    )

    proceso_nombre = st.selectbox(
        "Proceso",
        options=list(procesos_dict.keys())
    )

    zona = st.text_input("Zona")

    horas = st.number_input(
        "Horas laboradas",
        min_value=0.0,
        max_value=24.0
    )

    produccion = st.number_input(
        "Producción",
        min_value=0
    )

    aprobados = st.number_input(
        "Aprobados",
        min_value=0
    )

    rechazados = st.number_input(
        "Rechazados",
        min_value=0
    )

    observaciones = st.text_area("Observaciones", value="")

    submit = st.form_submit_button("Guardar reporte")

# =========================
# Guardar reporte
# =========================
if submit:
    semana = fecha_reporte.isocalendar()[1]
    año = fecha_reporte.year
    proceso_id = procesos_dict[proceso_nombre]

    try:
        cur.execute("""
            INSERT INTO reportes (
                tipo_reporte,
                cedula_personal,
                cedula_quien_reporta,
                supervisor_nombre,
                fecha_reporte,
                semana,
                año,
                horas,
                proceso_id,
                zona,
                produccion,
                aprobados,
                rechazados,
                tipo_evento_id,
                observaciones,
                perfil,
                puesto
            )
            VALUES (
                'produccion',
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                NULL,
                %s,
                %s,
                %s
            )
        """, (
            cedula_usuario,
            cedula_usuario,
            supervisor_nombre,
            fecha_reporte,
            semana,
            año,
            horas,
            proceso_id,
            zona,
            produccion,
            aprobados,
            rechazados,
            observaciones,
            perfil,
            usuario["puesto"]
        ))

        conn.commit()
        st.success("✅ Reporte de producción guardado correctamente")

    except Exception as e:
        conn.rollback()
        st.error("❌ Error al guardar el reporte")
        st.exception(e)
