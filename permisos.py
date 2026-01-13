import streamlit as st

# =====================================================
# Definición de permisos por perfil
# =====================================================
# 1 = Admin / Coordinador
# 2 = RRHH
# 3 = Operativo / Supervisor

PERMISOS_POR_PERFIL = {
    1: [
        "Login",
        "RRHH",
        "Produccion",
        "Eventos",
        "Historial",
        "Cerrar_Sesion"
    ],
    2: [
        "Login",
        "RRHH",
        "Cerrar_Sesion"
    ],
    3: [
        "Login",
        "Produccion",
        "Eventos",
        "Historial",
        "Cerrar_Sesion"
    ]
}


# =====================================================
# Validador de acceso reutilizable
# =====================================================
def validar_acceso(nombre_pagina: str):
    """
    Valida si el usuario autenticado puede acceder
    a la página solicitada según su perfil.
    """

    usuario = st.session_state.get("usuario")

    # ---- No ha iniciado sesión ----
    if not usuario:
        st.warning("Debe iniciar sesión para continuar")
        st.stop()

    perfil = usuario.get("perfil")

    # ---- Perfil inválido o sin permisos ----
    if perfil not in PERMISOS_POR_PERFIL:
        st.error("Perfil no reconocido")
        st.stop()

    # ---- Página no permitida ----
    if nombre_pagina not in PERMISOS_POR_PERFIL[perfil]:
        st.error("⛔ No tiene permiso para acceder a esta sección")
        st.stop()


# =====================================================
# Helper opcional (por si luego lo necesitas)
# =====================================================
def obtener_paginas_permitidas():
    """
    Devuelve la lista de páginas permitidas
    para el usuario autenticado.
    """
    usuario = st.session_state.get("usuario")
    if not usuario:
        return []

    return PERMISOS_POR_PERFIL.get(usuario["perfil"], [])
