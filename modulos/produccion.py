import streamlit as st
import json
from datetime import date
from db import get_connection
from permisos import validar_acceso


# =====================================================
# Cargar GeoJSON y crear lookup de complejidad
# =====================================================
@st.cache_data
def cargar_complejidad_geojson():
    with open("italia.geojson", "r", encoding="utf-8") as f:
        geojson = json.load(f)

    lookup = {}

    for feature in geojson.get("features", []):
        props = feature.get("properties", {})

        asignacion = props.get("Asignacion")
        bloque = props.get("BLOQUE")
        complejidad = props.get("Complejidad")

        if asignacion and bloque:
            bloque_fmt = str(bloque).zfill(3)
            key = f"{asignacion}{bloque_fmt}"
            lookup[key] = complejidad

    return lookup


def render():
    # =========================
    # Control de acceso
    # =========================
    validar_acceso("Produccion")

    usuario = st.session_state.get("usuario")

    perfil = usuario["perfil"]
    puesto = usuario["puesto"]
    cedula_usuario = usuario["cedula"]

    if perfil not in (1, 3):
        st.error("No tiene permiso para acceder a Producción")
        st.stop()

    st.title("📊 Reporte de Producción")

    conn = get_connection()
    cur = conn.cursor()

    # =========================
    # Procesos
    # =========================
    cur.execute("""
        SELECT id, nombre
        FROM procesos
        WHERE id <> 0
        ORDER BY id
    """)
    procesos = cur.fetchall()
    procesos_dict = {nombre: pid for pid, nombre in procesos}

    # =========================
    # Supervisor real
    # =========================
    cur.execute("""
        SELECT supervisor
        FROM personal
        WHERE cedula = %s
    """, (cedula_usuario,))
    row_sup = cur.fetchone()
    supervisor_nombre = row_sup[0] if row_sup else None

    # =========================
    # GeoJSON lookup
    # =========================
    lookup_complejidad = cargar_complejidad_geojson()

    # =========================
    # PROCESO (FUERA DEL FORM)
    # =========================
    proceso_nombre = st.selectbox(
        "Proceso",
        procesos_dict.keys()
    )
    proceso_id = procesos_dict[proceso_nombre]

    es_control_calidad = (proceso_id == 2)

    # =========================
    # ZONA (FUERA DEL FORM)
    # =========================
    asignaciones = [f"C{str(i).zfill(3)}" for i in range(1, 201)]
    bloques = [str(i).zfill(3) for i in range(1, 202)]

    col_z1, col_z2 = st.columns(2)
    with col_z1:
        asignacion = st.selectbox("Asignación", asignaciones)
    with col_z2:
        bloque = st.selectbox("Bloque", bloques)

    zona = f"{asignacion}{bloque}"
    complejidad = lookup_complejidad.get(zona)

    st.caption(f"📍 Zona: **{zona}**")
    if complejidad:
        st.caption(f"🧠 Complejidad detectada: **{complejidad}**")
    else:
        st.warning("⚠️ Esta zona no tiene complejidad definida en el mapa")

    # =========================
    # FORMULARIO
    # =========================
    with st.form("form_reporte_produccion"):
        fecha_reporte = st.date_input("Fecha", value=date.today())

        horas = st.number_input(
            "Horas laboradas",
            min_value=0.0,
            max_value=24.0,
            step=0.5
        )

        # -------- CONTROL DE CAMPOS --------
        if es_control_calidad:
            aprobados = st.number_input("Aprobados", min_value=0)
            rechazados = st.number_input("Rechazados", min_value=0)
            produccion = 0
        else:
            produccion = st.number_input("Producción", min_value=0)
            aprobados = 0
            rechazados = 0

        observaciones = st.text_area("Observaciones")

        submit = st.form_submit_button("Guardar reporte")

    # =========================
    # GUARDAR REPORTE
    # =========================
    if submit:
        if not complejidad:
            st.error("❌ No se puede guardar: la zona no tiene complejidad asignada")
            st.stop()

        semana = fecha_reporte.isocalendar()[1]
        año = fecha_reporte.year

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
                    complejidad,
                    produccion,
                    aprobados,
                    rechazados,
                    observaciones,
                    perfil,
                    puesto
                )
                VALUES (
                    'produccion',
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s
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
                complejidad,
                produccion,
                aprobados,
                rechazados,
                observaciones,
                perfil,
                puesto
            ))

            conn.commit()
            st.success("✅ Reporte guardado correctamente")

        except Exception as e:
            conn.rollback()
            st.error("❌ Error al guardar el reporte")
            st.exception(e)
