import streamlit as st
from datetime import date
from db import get_connection
from permisos import validar_acceso

def render():
    # =========================
    # Control de acceso
    # =========================
    validar_acceso("Eventos")

    usuario = st.session_state.get("usuario")

    perfil = usuario["perfil"]
    puesto = usuario["puesto"].lower()
    cedula_reporta = usuario["cedula"]
    nombre_usuario = usuario["nombre"]

    # Seguridad extra
    if perfil not in (1, 3):
        st.error("No tiene permiso para acceder a Reportes de Eventos")
        st.stop()

    st.title("📌 Reporte de Eventos")

    conn = get_connection()
    cur = conn.cursor()

    # =========================
    # Cargar tipos de evento
    # =========================
    cur.execute("""
        SELECT id, nombre
        FROM tipos_evento
        ORDER BY nombre
    """)
    tipos_evento = cur.fetchall()

    if not tipos_evento:
        st.error("No existen tipos de evento registrados")
        st.stop()

    # Restricción para Operario Catastral
    if puesto == "operario catastral":
        tipos_evento = [
            (id_, nombre)
            for id_, nombre in tipos_evento
            if id_ in (3, 17)
        ]

    if not tipos_evento:
        st.error("No existen tipos de evento disponibles para su perfil")
        st.stop()

    tipos_evento_dict = {nombre: id_ for id_, nombre in tipos_evento}

    # =========================
    # Cargar personal según jerarquía
    # =========================
    if puesto == "coordinador":
        cur.execute("""
            SELECT cedula, nombre_completo, perfil, puesto, supervisor
            FROM personal
            WHERE estado = 'activo'
            ORDER BY nombre_completo
        """)
    else:
        cur.execute("""
            SELECT cedula, nombre_completo, perfil, puesto, supervisor
            FROM personal
            WHERE estado = 'activo'
              AND supervisor = %s
            ORDER BY nombre_completo
        """, (nombre_usuario,))

    personal = cur.fetchall()

    if not personal:
        st.error("No existe personal disponible para reportar")
        st.stop()

    personal_dict = {
        f"{nombre} ({ced})": {
            "cedula": ced,
            "perfil": perfil_p,
            "puesto": puesto_p,
            "supervisor": supervisor_p
        }
        for ced, nombre, perfil_p, puesto_p, supervisor_p in personal
    }

    # =========================
    # Formulario
    # =========================
    with st.form("form_reporte_evento"):
        fecha_reporte = st.date_input(
            "Fecha del evento",
            value=date.today()
        )

        tipo_evento_nombre = st.selectbox(
            "Tipo de evento",
            options=list(tipos_evento_dict.keys())
        )

        horas = st.number_input(
            "Horas",
            min_value=0.0,
            max_value=24.0,
            step=0.5
        )

        # =========================
        # Selección de personal
        # =========================
        if puesto == "operario catastral":
            personal_seleccionado = [
                key for key, val in personal_dict.items()
                if val["cedula"] == cedula_reporta
            ]
            st.info("Como Operario Catastral, solo puede reportarse a sí mismo.")
        else:
            personal_seleccionado = st.multiselect(
                "Personal al que aplica el evento",
                options=list(personal_dict.keys())
            )

        observaciones = st.text_area(
            "Observaciones (opcional)",
            value=""
        )

        submit = st.form_submit_button("Guardar evento")

    # =========================
    # Guardar eventos
    # =========================
    if submit:
        if not personal_seleccionado:
            st.warning("Debe seleccionar al menos una persona")
            st.stop()

        semana = fecha_reporte.isocalendar()[1]
        año = fecha_reporte.year
        tipo_evento_id = tipos_evento_dict[tipo_evento_nombre]

        try:
            for persona in personal_seleccionado:
                datos = personal_dict[persona]

                cedula_personal = datos["cedula"]
                perfil_personal = datos["perfil"]
                puesto_personal = datos["puesto"]

                # Obtener supervisor REAL del reportado
                cur.execute("""
                    SELECT supervisor
                    FROM personal
                    WHERE cedula = %s
                """, (cedula_personal,))

                row_sup = cur.fetchone()
                supervisor_nombre = row_sup[0] if row_sup else None

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
                        'evento',
                        %s, %s, %s, %s, %s, %s,
                        %s, 0, 0, 0, 0, 0,
                        %s, %s, %s, %s
                    )
                """, (
                    cedula_personal,
                    cedula_reporta,
                    supervisor_nombre,
                    fecha_reporte,
                    semana,
                    año,
                    horas,
                    tipo_evento_id,
                    observaciones,
                    perfil_personal,
                    puesto_personal
                ))

            conn.commit()
            st.success("✅ Evento(s) registrado(s) correctamente")

        except Exception as e:
            conn.rollback()
            st.error("❌ Error al guardar el evento")
            st.exception(e)
