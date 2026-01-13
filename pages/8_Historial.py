import streamlit as st
import pandas as pd
from db import get_connection

st.title("📈 Historial de Reportes")

# =========================
# Control de acceso
# =========================
usuario = st.session_state.get("usuario")

if not usuario:
    st.warning("Debe iniciar sesión")
    st.stop()

perfil = usuario["perfil"]        # 1=Admin/Coordinador, 2=Operador, 3=Supervisor
puesto = usuario["puesto"].lower()
cedula_usuario = usuario["cedula"]
nombre_usuario = usuario["nombre"]

conn = get_connection()

# =========================
# Filtro de fechas
# =========================
col1, col2 = st.columns(2)
with col1:
    fecha_inicio = st.date_input("Desde")
with col2:
    fecha_fin = st.date_input("Hasta")

# =========================
# Selector de alcance según perfil
# =========================
where_extra = ""
params_base = [fecha_inicio, fecha_fin]

# -------- OPERADOR --------
if perfil == 2:
    where_extra = " AND r.cedula_personal = %s"
    params_base.append(cedula_usuario)

# -------- SUPERVISOR --------
elif perfil == 3:
    opcion = st.radio(
        "Ver reportes de:",
        ["Propios", "Operadores a cargo"],
        horizontal=True
    )

    if opcion == "Propios":
        where_extra = " AND r.cedula_personal = %s"
        params_base.append(cedula_usuario)
    else:
        where_extra = " AND r.supervisor_nombre = %s"
        params_base.append(nombre_usuario)

# -------- COORDINADOR / ADMIN --------
elif perfil == 1:
    opcion = st.radio(
        "Ver reportes:",
        ["Totales", "Propios"],
        horizontal=True
    )

    if opcion == "Propios":
        where_extra = " AND r.cedula_personal = %s"
        params_base.append(cedula_usuario)
    else:
        where_extra = ""

# =========================
# REPORTES DE PRODUCCIÓN
# =========================
st.subheader("📊 Reportes de Producción")

query_prod = f"""
SELECT 
    r.fecha_reporte,
    p.nombre_completo AS persona,
    r.supervisor_nombre AS supervisor,
    r.zona,
    r.horas,
    r.produccion,
    r.aprobados,
    r.rechazados,
    r.observaciones
FROM reportes r
JOIN personal p ON p.cedula = r.cedula_personal
WHERE r.tipo_reporte = 'produccion'
AND r.fecha_reporte BETWEEN %s AND %s
{where_extra}
ORDER BY r.fecha_reporte, persona
"""

df_prod = pd.read_sql(query_prod, conn, params=params_base)
st.dataframe(df_prod, use_container_width=True)

# =========================
# REPORTES DE EVENTOS
# =========================
st.subheader("🗂️ Reportes de Eventos")

query_eventos = f"""
SELECT 
    r.fecha_reporte,
    p.nombre_completo AS persona,
    r.supervisor_nombre AS supervisor,
    r.horas,
    te.nombre AS tipo_evento,
    r.observaciones
FROM reportes r
JOIN personal p ON p.cedula = r.cedula_personal
LEFT JOIN tipos_evento te ON te.id = r.tipo_evento_id
WHERE r.tipo_reporte = 'evento'
AND r.fecha_reporte BETWEEN %s AND %s
{where_extra}
ORDER BY r.fecha_reporte, persona
"""

df_eventos = pd.read_sql(query_eventos, conn, params=params_base)
st.dataframe(df_eventos, use_container_width=True)

# =========================
# RESUMEN DIARIO DE HORAS (POR PERSONA)
# =========================
st.subheader("⏱️ Resumen Diario de Horas por Persona")

query_horas = f"""
SELECT 
    r.fecha_reporte,
    p.nombre_completo AS persona,
    SUM(r.horas) AS total_horas
FROM reportes r
JOIN personal p ON p.cedula = r.cedula_personal
WHERE r.fecha_reporte BETWEEN %s AND %s
{where_extra}
GROUP BY r.fecha_reporte, p.nombre_completo
ORDER BY r.fecha_reporte, persona
"""

df_horas = pd.read_sql(query_horas, conn, params=params_base)

# Validación flexible de 8.5 horas (por persona)
df_horas["estado"] = df_horas["total_horas"].apply(
    lambda x: "✅ OK" if 8.4 <= float(x) <= 8.6 else "⚠️ Revisar"
)

st.dataframe(df_horas, use_container_width=True)
