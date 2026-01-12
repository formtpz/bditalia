import streamlit as st
import pandas as pd
from db import get_connection

st.title("📈 Historial de Reportes")

usuario = st.session_state.get("usuario")

if not usuario:
    st.warning("Debe iniciar sesión")
    st.stop()

perfil = usuario["perfil"]
puesto = usuario["puesto"]
cedula = usuario["cedula"]

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
    r.fecha_reporte,
    r.horas,
    r.zona,
    r.aprobados,
    r.rechazados,
    r.produccion,
    r.observaciones
FROM reportes r
WHERE r.tipo_reporte = 'produccion'
AND r.fecha_reporte BETWEEN %s AND %s
"""

params = [fecha_inicio, fecha_fin]

if perfil != 1:
    query_prod += " AND r.cedula_personal = %s"
    params.append(cedula)

df_prod = pd.read_sql(query_prod, conn, params=params)
st.dataframe(df_prod, use_container_width=True)

# =========================
# EVENTOS
# =========================
st.subheader("🗂️ Reportes de Eventos")

query_eventos = """
SELECT 
    r.fecha_reporte,
    r.horas,
    te.nombre AS tipo_evento,
    r.observaciones
FROM reportes r
LEFT JOIN tipos_evento te ON te.id = r.tipo_evento_id
WHERE r.tipo_reporte = 'evento'
AND r.fecha_reporte BETWEEN %s AND %s
"""

params = [fecha_inicio, fecha_fin]

if perfil != 1:
    query_eventos += " AND r.cedula_personal = %s"
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

query_horas += """
GROUP BY fecha_reporte
ORDER BY fecha_reporte
"""

df_horas = pd.read_sql(query_horas, conn, params=params)

# Validación flexible de 8.5 horas
df_horas["estado"] = df_horas["total_horas"].apply(
    lambda x: "✅ OK" if 8.4 <= float(x) <= 8.6 else "⚠️ Revisar"
)

st.dataframe(df_horas, use_container_width=True)
