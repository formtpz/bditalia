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
    # Cargar REGIONES reales
    # =========================
    cur.execute("""
        SELECT DISTINCT region
        FROM asignaciones
        ORDER BY region
    """)
    lista_regiones = [row[0] for row in cur.fetchall()]

    if not lista_regiones:
        st.error("No existen regiones registradas en la tabla asignaciones")
        st.stop()

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
    # REGION / ASIGNACION / BLOQUE
    # =========================
    col1, col2, col3 = st.columns(3)

    # Región
    with col1:
        region = st.selectbox(
            "Región",
            lista_regiones
        )

    # Asignaciones según región
    cur.execute("""
        SELECT DISTINCT asignacion
        FROM asignaciones
        WHERE region = %s
        ORDER BY asignacion
    """, (region,))
    lista_asignaciones = [row[0] for row in cur.fetchall()]

    if not lista_asignaciones:
        st.warning("No hay asignaciones para esta región")
        st.stop()

    # Asignación
    with col2:
        asignacion = st.selectbox(
            "Asignación",
            lista_asignaciones
        )

    # Bloques según región + asignación
    cur.execute("""
        SELECT bloque
        FROM asignaciones
        WHERE region = %s
          AND asignacion = %s
        ORDER BY bloque
    """, (region, asignacion))
    lista_bloques = [row[0] for row in cur.fetchall()]

    if not lista_bloques:
        st.warning("No hay bloques para esta asignación")
        st.stop()

    # Bloque
    with col3:
        bloque = st.selectbox(
            "Bloque",
            lista_bloques
        )

    # =========================
    # Obtener complejidad real
    # =========================
    cur.execute("""
        SELECT complejidad
        FROM asignaciones
        WHERE region = %s
          AND asignacion = %s
          AND bloque = %s
        LIMIT 1
    """, (region, asignacion, bloque))

    row_comp = cur.fetchone()
    complejidad = row_comp[0] if row_comp else None

    zona = f"{asignacion}{str(bloque).zfill(3)}"

    st.caption(f"📍 Región: **{region}**")
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
                    region,
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
                    %s, %s, %s, %s, %s
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
                region,
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

