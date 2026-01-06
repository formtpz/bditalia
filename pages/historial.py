import streamlit as st
import pandas as pd
from db import get_connection

st.title("📈 Historial de Reportes")

usuario = st.session_state.get("usuario")

if not st.session_state.get("authenticated"):
    st.warning("Debe iniciar sesión")
    st.stop()

cedula = st.session_state.get("cedula")
perfil = st.session_state.get("perfil")

conn = get_connection()

# =========================
# FILTRO DE FECHAS
# =========================
col1, col2 = st.columns(2)
with col1:
    fecha_inicio = st.date_input("Desde")
with col2:
    fecha_fin = st.date_input("Hasta")

# =========================
# PRODUCCIÓN
# =========================
st.subheader("📊 Reportes de Producción")

query_prod = """
SELECT 
    fecha_reporte,
    horas,
    zona,
    aprobados,
    rechazados,
    (aprobados + rechazados) AS produccion,
    observaciones
FROM reportes
WHERE tipo_reporte = 'produccion'
AND fecha_reporte BETWEEN %s AND %s
"""

params = [fecha_inicio, fecha_fin]

if perfil != 1:  # no admin
    query_prod += " AND cedula_personal = %s"
    params.append(cedula)

df_prod = pd.read_sql(query_prod, conn, params=params)

st.dataframe(df_prod, use_container_width=True)

# =========================
# EVENTOS
# =========================
st.subheader("🗂️ Reportes de Eventos")

query_eventos = """
SELECT 
    fecha_reporte,
    horas,
    tipo_evento_id,
    observaciones
FROM reportes
WHERE tipo_reporte = 'evento'
AND fecha_reporte BETWEEN %s AND %s
"""

params = [fecha_inicio, fecha_fin]

if perfil != 1:
    query_eventos += " AND cedula_personal = %s"
    params.append(cedula)

df_eventos = pd.read_sql(query_eventos, conn, params=params)

st.dataframe(df_eventos, use_container_width=True)

# =========================
# RESUMEN DIARIO DE HORAS
# =========================
st.subheader("⏱️ Resumen Diario de Horas")

query_horas = """
SELECT 
    fecha_reporte,
    SUM(horas) AS total_horas
FROM reportes
WHERE fecha_reporte BETWEEN %s AND %s
"""

params = [fecha_inicio, fecha_fin]

if perfil != 1:
    query_horas += " AND cedula_personal = %s"
    params.append(cedula)

query_horas += " GROUP BY fecha_reporte ORDER BY fecha_reporte"

df_horas = pd.read_sql(query_horas, conn, params=params)

# Validación 8.5
df_horas["estado"] = df_horas["total_horas"].apply(
    lambda x: "✅ OK" if x == 8.5 else "⚠️ Revisar"
)

st.dataframe(df_horas, use_container_width=True)
