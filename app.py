import streamlit as st
from permisos import PERMISOS_POR_PERFIL

# =========================
# Configuración general
# =========================
st.set_page_config(
    page_title="Sistema de Reportes",
    page_icon="📊",
    layout="wide"
)

usuario = st.session_state.get("usuario")

# =========================
# USUARIO NO LOGUEADO → LOGIN
# =========================
if not usuario:
    from modulos.login import render
    render()
    st.stop()

# =========================
# USUARIO LOGUEADO → MENÚ DINÁMICO
# =========================
perfil = usuario["perfil"]

opciones = PERMISOS_POR_PERFIL.get(perfil, [])

with st.sidebar:
    st.image("logo.png", use_container_width=True, width=12)

    st.markdown("### Menú")
    opcion = st.radio("Seleccione una opción", opciones)

# =========================
# ROUTER DE MÓDULOS
# =========================
if opcion == "Produccion":
    from modulos.produccion import render
    render()

elif opcion == "RRHH":
    from modulos.rrhh import render
    render()

elif opcion == "Eventos":
    from modulos.eventos import render
    render()

elif opcion == "Historial":
    from modulos.historial import render
    render()

elif opcion == "Cerrar_Sesion":
    from modulos.cerrar_sesion import render
    render()
