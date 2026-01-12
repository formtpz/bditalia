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
cedula_reporta = usuario["cedula"]

if perfil not in (1, 2, 3):
    st.error("No tiene permiso para acceder a esta sección")
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

# =========================
# Restricción de eventos para Operario Catastral
# =========================
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
# Cargar personal activo
# =========================
cur.execute("""
    SELECT cedula, nombre_completo, perfil, puesto
    FROM personal
    WHERE estado = 'activo'
    ORDER BY nombre_completo
""")

personal = cur.fetchall()

personal_dict = {
    f"{nombre} ({ced})": {
        "cedula": ced,
        "perfil": perfil_p,
        "puesto": puesto_p
    }
    for ced, nombre, perfil_p, puesto_p in personal
}

# =========================
# Formulario
# =========================
with st.form("form_reporte_evento"):
    st.subheader("Datos del evento")

    fecha_reporte = st.date_input("Fecha del evento", value=date.today())

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
        # Solo autoreporte
        personal_seleccionado = [
           key for key, val in personal_dict.items()
            if val["cedula"] == cedula_reporta
        ]
        st.info("Como Operario Catastral, solo puede reportarse a sí mismo.")
    else:
        # Admin y Supervisor
        personal_seleccionado = st.multiselect(
            "Personal al que aplica el evento",
            options=list(personal_dict.keys()),
            default=[
                key for key, val in personal_dict.items()
                if val["cedula"] == cedula_reporta
            ]
        )
    observaciones = st.text_area("Observaciones (opcional)", value="") 
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

            cur.execute("""
            INSERT INTO reportes (
                tipo_reporte,
                cedula_personal,
                cedula_quien_reporta,
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
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                NULL,
                NULL,
                0,
                0,
                0,
                %s,
                %s,
                %s,
                %s
            )
        """, (
            cedula_personal,
            cedula_reporta,
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
