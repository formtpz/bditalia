import streamlit as st
import pandas as pd
from db import get_connection
from permisos import validar_acceso


def render():
    # =========================
    # Control de acceso
    # =========================
    validar_acceso("Dashboards")

    usuario = st.session_state["usuario"]

    if usuario["perfil"] != 1:
        st.error("⛔ Acceso exclusivo para Administrador / Coordinador")
        st.stop()

    st.title("📊 Dashboards")

    conn = get_connection()

    # =====================================================
    # A) RESUMEN DE PERSONAL ACTIVO
    # =====================================================
    st.subheader("👥 Personal activo")

    df_personal = pd.read_sql("""
        SELECT
            puesto,
            COUNT(*) AS cantidad
        FROM personal
        WHERE estado = 'activo'
        GROUP BY puesto
        ORDER BY puesto
    """, conn)

    total_personal = df_personal["cantidad"].sum()

    df_total = pd.DataFrame(
        [{"puesto": "TOTAL", "cantidad": total_personal}]
    )

    df_personal_resumen = pd.concat(
        [df_total, df_personal],
        ignore_index=True
    )

    st.dataframe(df_personal_resumen, use_container_width=True)

    st.divider()

    # =====================================================
    # FILTRO GLOBAL DE FECHAS
    # =====================================================
    st.subheader("📅 Filtro de fechas")

    col1, col2 = st.columns(2)
    with col1:
        fecha_inicio = st.date_input("Desde")
    with col2:
        fecha_fin = st.date_input("Hasta")

    st.divider()

    # =====================================================
    # B) PRODUCCIÓN POR OPERADOR
    # =====================================================
    st.subheader("🏗️ Producción total por operador")

    df_prod = pd.read_sql("""
        SELECT
            p.nombre_completo AS operador,
            SUM(r.produccion) AS total_produccion
        FROM reportes r
        JOIN personal p ON p.cedula = r.cedula_personal
        WHERE r.tipo_reporte = 'produccion'
          AND r.fecha_reporte BETWEEN %s_
