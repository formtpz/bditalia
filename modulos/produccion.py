import streamlit as st
from datetime import date
from db import get_connection
from permisos import validar_acceso


def render():
    # =========================
    # Control de acceso
    # =========================
    validar_acceso("Produccion")

    usuario = st.session_state.get("usuario")

    perfil = usuario["perfil"]
    puesto = usuario["puesto"]
    cedula_usuario = usuario["cedula"]

    # Seguridad extra
    if perfil not in (1, 3):
        st.error("No tiene permiso para acceder a Producción")
        st.stop()

    st.title("📊 Reporte de Producción")

    conn = get_connection()
    cur = conn.cursor()

    # =========================
    # Cargar procesos (excluye proceso 0)
    # =========================
    cur.execute("""
        SELECT id, nombre
        FROM procesos
        WHERE id <> 0
        ORDER BY nombre
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
    # Formulario
    # =========================
    with st.form("form_reporte_produccion"):
        fecha_reporte = st.date_input("Fecha", value=date.today())

        proceso_nombre = st.selectbox(
            "Proceso",
            procesos_dict.keys()
        )

        # =========================
        # Zona (Asignación + Bloque)
        # =========================
        asignaciones = [f"C{str(i).zfill(3)}" for i in range(1, 101)]
        bloques = list(range(1, 101))

        col_z1, col_z2 = st.columns(2)

        with col_z1:
            asignacion = st.selectbox(
                "Asignación",
                asignaciones
            )

        with col_z2:
            bloque = st.selectbox(
                "Bloque",
                bloques
            )

        # Zona final concatenada
        zona = f"{asignacion}{bloque}"

        # Vista opcional de confirmación
        st.caption(f"📍 Zona generada: **{zona}**")

        horas = st.number_input(
            "Horas laboradas",
            min_value=0.0,
            max_value=24.0,
            step=0.5
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

        observaciones = st.text_area("Observaciones")

        submit = st.form_submit_button("Guardar reporte")

    # =========================
    # Guardar reporte
    # =========================
    if submit:
        semana = fecha_reporte.isocalendar()[1]
        año = fecha_reporte.year
        proceso_id = procesos_dict[proceso_nombre]

        # Validación extra (seguridad)
        if proceso_id == 0:
            st.error("❌ Proceso inválido. Seleccione un proceso válido.")
            st.stop()

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
                    observaciones,
                    perfil,
                    puesto
                )
                VALUES (
                    'produccion',
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s
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
                puesto
            ))

            conn.commit()
            st.success("✅ Reporte guardado correctamente")

        except Exception as e:
            conn.rollback()
            st.error("❌ Error al guardar el reporte")
            st.exception(e)

