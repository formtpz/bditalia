import streamlit as st
import pandas as pd
import json
import pydeck as pdk
from datetime import date
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
    st.subheader("📅 Filtro de fechas (KPIs)")

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
            SUM(COALESCE(r.produccion::numeric, 0)) AS total_produccion
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
        st.bar_chart(df_prod.set_index("operador"))
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

    st.divider()

    # =====================================================
    # D) MAPA 3D DE AVANCE POR BLOQUES
    # =====================================================
    st.subheader("🗺️ Avance por bloques")

    # ---------- filtros de fecha del mapa ----------
    col1, col2 = st.columns(2)
    with col1:
        fecha_ini_map = st.date_input(
            "Inicio (mapa)",
            value=fecha_inicio,
            key="map_ini"
        )
    with col2:
        fecha_fin_map = st.date_input(
            "Fin (mapa)",
            value=fecha_fin,
            key="map_fin"
        )

    # ---------- zonas reportadas ----------
    df_zonas = pd.read_sql("""
        SELECT DISTINCT zona
        FROM reportes
        WHERE tipo_reporte = 'produccion'
          AND zona IS NOT NULL
          AND fecha_reporte BETWEEN %s AND %s
    """, conn, params=[fecha_ini_map, fecha_fin_map])

    zonas_reportadas = set(df_zonas["zona"].str.strip())

    # ---------- cargar geojson ----------
    with open("italia.geojson", "r", encoding="utf-8") as f:
        geojson = json.load(f)

    features = []

    for feat in geojson["features"]:
        asignacion = str(feat["properties"]["Asignacion"]).strip()
        bloque = str(feat["properties"]["BLOQUE"]).strip()
        zona = f"{asignacion}{bloque}"

        completado = zona in zonas_reportadas

        features.append({
            "geometry": feat["geometry"],
            "elevation": 120 if completado else 0,
            "fill_color": [220, 220, 220, 80] if not completado else [31, 119, 255, 180],
            "zona": zona,
            "asignacion": asignacion,
            "bloque": bloque
        })

    geojson_3d = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": f["geometry"],
                "properties": {
                    "elevation": f["elevation"],
                    "fill_color": f["fill_color"],
                    "zona": f["zona"],
                    "asignacion": f["asignacion"],
                    "bloque": f["bloque"],
                }
            }
            for f in features
        ]
    }

    # ---------- capa 3D ----------
    layer = pdk.Layer(
        "PolygonLayer",
        data=geojson_3d["features"],
        get_polygon="geometry.coordinates",

    # Relleno
        get_fill_color="properties.fill_color",

    # Elevación 3D
        get_elevation="properties.elevation",
        elevation_scale=1,
        extruded=True,

    # 🔴 CONTORNO (CLAVE)
        stroked=True,
        get_line_color=[80, 80, 80, 200],
        line_width_min_pixels=1,

    # Interacción
        pickable=True,
        auto_highlight=True,
    )


    # ---------- vista inicial ----------
    view_state = pdk.ViewState(
        latitude=41.9,
        longitude=12.5,
        zoom=6,
        pitch=55,
        bearing=0
    )

    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={
            "html": """
            <b>Zona:</b> {zona}<br/>
            <b>Asignación:</b> {asignacion}<br/>
            <b>Bloque:</b> {bloque}
            """,
            "style": {
                "backgroundColor": "#1f77ff",
                "color": "white"
            }
        }
    )

    st.pydeck_chart(deck, use_container_width=True)
