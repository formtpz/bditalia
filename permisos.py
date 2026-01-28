import streamlit as st

PERMISOS_POR_PERFIL = {
    1: ["Dashboards","RRHH","Cargar Asignaciones", "Producción", "Eventos", "Historial", "Correcciones", "Cerrar Sesion"],
    2: ["RRHH", "Cerrar Sesion"],
    3: ["Producción", "Asignación de Producción", "Eventos", "Historial","Correcciones", "Cerrar Sesion"]
}


def validar_acceso(nombre_pagina: str):
    usuario = st.session_state.get("usuario")

    # =========================
    # USUARIO NO LOGUEADO
    # =========================
    if not usuario:
        st.warning("Debe iniciar sesión para continuar")
        st.stop()

    perfil = usuario.get("perfil")

    # =========================
    # PERFIL NO VÁLIDO
    # =========================
    if perfil not in PERMISOS_POR_PERFIL:
        st.error("Perfil no reconocido")
        st.stop()

    # =========================
    # PÁGINA NO PERMITIDA
    # =========================
    if nombre_pagina not in PERMISOS_POR_PERFIL[perfil]:
        st.error("⛔ No tiene permiso para acceder a esta sección")
        st.stop()
