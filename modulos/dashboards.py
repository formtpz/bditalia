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

    df_ = pd.DataFrame(
        [{"puesto": "Total Personal Proyecto", "cantidad": total_personal}]
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
          AND r.fecha_reporte BETWEEN %s AND %s
        GROUP BY p.nombre_completo
        ORDER BY total_produccion DESC
    """, conn, params=[fecha_inicio, fecha_fin])

    if df_prod.empty:
        st.info("No hay datos de producción en el rango seleccionado")
    else:
        st.bar_chart(
            df_prod.set_index("operador")
        )

        st.dataframe(df_prod, use_container_width=True)

    st.divider()

    # =====================================================
    # C) CONTEO DE EVENTOS POR CATEGORÍA
    # =====================================================
    st.subheader("🗂️ Eventos por categoría")

    df_eventos = pd.read_sql("""
        SELECT
            te.nombre AS tipo_evento,
            COUNT(*) AS cantidad
        FROM reportes r
        LEFT JOIN tipos_evento te
            ON te.id = r.tipo_evento_id
        WHERE r.tipo_reporte = 'evento'
          AND r.fecha_reporte BETWEEN %s AND %s
        GROUP BY te.nombre
        ORDER BY cantidad DESC
    """, conn, params=[fecha_inicio, fecha_fin])

    if df_eventos.empty:
        st.info("No hay eventos registrados en el rango seleccionado")
    else:
        st.dataframe(df_eventos, use_container_width=True)
