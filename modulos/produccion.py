import streamlit as st
from datetime import date
from db import get_connection
from permisos import validar_acceso


def render():

    # =========================
    # Control de acceso
    # =========================
    validar_acceso("Reportes Producción")

    usuario = st.session_state.get("usuario")

    perfil = usuario["perfil"]
    puesto = usuario["puesto"]
    cedula_usuario = usuario["cedula"]

    if perfil not in (1, 3, 4):
        st.error("No tiene permiso para acceder a Producción")
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
        WHERE id <> 0
        ORDER BY id
    """)
    procesos = cur.fetchall()
    procesos_dict = {nombre: pid for pid, nombre in procesos}

    # =========================
    # Obtener supervisor real
    # =========================
    cur.execute("""
        SELECT supervisor
        FROM personal
        WHERE cedula = %s
    """, (cedula_usuario,))
    row_sup = cur.fetchone()
    supervisor_nombre = row_sup[0] if row_sup else None

    # =========================
    # Cargar ASIGNACIONES reales
    # =========================
    cur.execute("""
        SELECT DISTINCT asignacion
        FROM asignaciones
        ORDER BY asignacion
    """)
    lista_asignaciones = [row[0] for row in cur.fetchall()]

    # =========================
    # PROCESO
    # =========================
    proceso_nombre = st.selectbox(
        "Proceso",
        procesos_dict.keys()
    )
    proceso_id = procesos_dict[proceso_nombre]

    es_control_calidad = (proceso_id == 2)

    # =========================
    # REGION / ASIGNACION / BLOQUE (MANUAL)
    # =========================
    col1, col2 = st.columns(2)

    with col1:
        asignacion = st.selectbox(
            "Asignación",
            lista_asignaciones
        )

    # Bloques según asignación seleccionada
    cur.execute("""
        SELECT bloque
        FROM asignaciones
        WHERE asignacion = %s
        ORDER BY bloque
    """, (asignacion,))

    lista_bloques = [row[0] for row in cur.fetchall()]

    with col2:
        bloque = st.selectbox(
            "Bloque",
            lista_bloques
        )

    # Obtener complejidad real desde BD
    cur.execute("""
        SELECT complejidad
        FROM asignaciones
        WHERE asignacion = %s
          AND bloque = %s
        LIMIT 1
    """, (asignacion, bloque))

    row_comp = cur.fetchone()
    complejidad = row_comp[0] if row_comp else None

    zona = f"{asignacion}{str(bloque).zfill(3)}"

    st.caption(f"📍 Zona: **{zona}**")

    if complejidad:
        st.caption(f"🧠 Complejidad detectada: **{complejidad}**")
    else:
        st.warning("⚠️ Esta zona no tiene complejidad definida")

    # =========================
    # FORMULARIO
    # =========================
    with st.form("form_reporte_produccion"):

        fecha_reporte = st.date_input(
            "Fecha",
            value=date.today()
        )

        horas = st.number_input(
            "Horas laboradas",
            min_value=0.0,
            max_value=24.0,
            step=0.5
        )

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
            st.error("❌ No se puede guardar: la zona no tiene complejidad")
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
