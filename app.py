import streamlit as st
from permisos import PERMISOS_POR_PERFIL

hide_streamlit_style = """
                <style>
                div[data-testid="stToolbar"] {
                visibility: hidden;
                height: 0%;
                position: fixed;
                }
                div[data-testid="stDecoration"] {
                visibility: hidden;
                height: 0%;
                position: fixed;
                }
                div[data-testid="stStatusWidget"] {
                visibility: Visible;
                height: 0%;
                position: fixed;
                }
                #MainMenu {
                visibility: hidden;
                height: 0%;
                }
                header {
                visibility: hidden;
                height: 0%;
                }
                footer {
                visibility: hidden;
                height: 0%;
                }
                </style>
                """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

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
    st.image("logo.png", width=1200)

    st.markdown("### Menú")
    opcion = st.radio("Seleccione una opción", opciones)

# =========================
# ROUTER DE MÓDULOS
# =========================
if opcion == "Dashboards":
    from modulos.dashboards import render
    render()

elif opcion == "Asignación de Producción":
    from modulos.asignaciones import render
    render()

elif opcion == "Cargar Asignaciones":
    from modulos.cargar_asignaciones import render
    render()

elif opcion == "Reportes Producción":
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
  
elif opcion == "Correcciones":
    from modulos.correcciones import render
    render()

elif opcion == "Cerrar Sesion":
    from modulos.cerrar_sesion import render
    render()


