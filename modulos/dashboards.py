import streamlit as st
import pandas as pd
import json
import folium
from streamlit_folium import st_folium
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
    # D) MAPA DE AVANCE POR BLOQUES
    # =====================================================
    st.subheader("🗺️ Avance por bloques")

    # --- zonas ya reportadas ---
    df_zonas = pd.read_sql("""
        SELECT DISTINCT zona
        FROM reportes
        WHERE tipo_reporte = 'produccion'
          AND zona IS NOT NULL
    """, conn)

    zonas_reportadas = set(df_zonas["zona"].str.strip())

    # --- cargar geojson ---
    with open("italia.geojson", "r", encoding="utf-8") as f:
        geojson_data = json.load(f)

    # --- calcular avance ---
    avance = {}

    for feature in geojson_data["features"]:
        asignacion = str(feature["properties"]["Asignacion"]).strip()
        bloque = str(feature["properties"]["BLOQUE"]).strip()
        zona_concat = f"{asignacion}{bloque}"

        if asignacion not in avance:
            avance[asignacion] = {"total": 0, "completados": 0}

        avance[asignacion]["total"] += 1

        if zona_concat in zonas_reportadas:
            avance[asignacion]["completados"] += 1

    # --- mostrar % ---
    cols = st.columns(len(avance))
    for col, (a, v) in zip(cols, avance.items()):
        porcentaje = round((v["completados"] / v["total"]) * 100, 1)
        col.metric(
            label=f"Asignación {a}",
            value=f"{porcentaje}%",
            delta=f"{v['completados']} / {v['total']}"
        )

    # --- mapa base ---
    m = folium.Map(
        location=[41.9, 12.5],
        zoom_start=6,
        tiles="OpenStreetMap"
    )

    # --- estilo ---
    def style_function(feature):
        asignacion = str(feature["properties"]["Asignacion"]).strip()
        bloque = str(feature["properties"]["BLOQUE"]).strip()
        zona = f"{asignacion}{bloque}"

        if zona in zonas_reportadas:
            return {
                "fillColor": "#1f77ff",
                "color": "#1f77ff",
                "weight": 1,
                "fillOpacity": 0.7,
            }
        else:
            return {
                "fillColor": "#d9d9d9",
                "color": "#888888",
                "weight": 0.5,
                "fillOpacity": 0.4,
            }

    folium.GeoJson(
        geojson_data,
        name="Bloques",
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=["Asignacion", "BLOQUE"],
            aliases=["Asignación", "Bloque"]
        )
    ).add_to(m)

    folium.LayerControl().add_to(m)

    st_folium(m, use_container_width=True, height=600)

