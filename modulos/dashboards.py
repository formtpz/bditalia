import streamlit as st
import pandas as pd
import json
import pydeck as pdk
from db import get_connection
from permisos import validar_acceso


def normalizar_bloque(bloque):
    return str(bloque).zfill(3)


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

    col1, col2 = st.columns(2)
    with col1:
        fecha_ini_map = st.date_input(
            "Desde (mapa)",
            value=fecha_inicio,
            key="map_ini"
        )
    with col2:
        fecha_fin_map = st.date_input(
            "Hasta (mapa)",
            value=fecha_fin,
            key="map_fin"
        )

    # -----------------------------------------------------
    # Zonas reportadas + operadores
    # -----------------------------------------------------
    df_zonas = pd.read_sql("""
        SELECT
            r.zona,
            p.nombre_completo AS operador
        FROM reportes r
        JOIN personal p ON p.cedula = r.cedula_personal
        WHERE r.tipo_reporte = 'produccion'
          AND r.zona IS NOT NULL
          AND r.fecha_reporte BETWEEN %s AND %s
    """, conn, params=[fecha_ini_map, fecha_fin_map])

    zona_operadores = {}

    for _, row in df_zonas.iterrows():
        zona = row["zona"].strip()
        operador = row["operador"]

        zona_operadores.setdefault(zona, set()).add(operador)

    zonas_reportadas = set(zona_operadores.keys())

    # -----------------------------------------------------
    # Cargar GeoJSON
    # -----------------------------------------------------
    with open("italia.geojson", "r", encoding="utf-8") as f:
        geojson = json.load(f)

    # -----------------------------------------------------
    # Pintar bloques según avance
    # -----------------------------------------------------
    for feature in geojson["features"]:
        asignacion = str(feature["properties"]["Asignacion"]).strip()
        bloque = normalizar_bloque(feature["properties"]["BLOQUE"])
        zona = f"{asignacion}{bloque}"

        if zona in zonas_reportadas:
            feature["properties"]["color"] = [31, 119, 255, 180]  # Azul
            feature["properties"]["operador"] = ", ".join(
                sorted(zona_operadores.get(zona, []))
            )
        else:
            feature["properties"]["color"] = [220, 220, 220, 140]  # Gris
            feature["properties"]["operador"] = "—"

    if not zonas_reportadas:
        st.info(
            "ℹ️ No existen reportes de producción en el rango seleccionado. "
            "Se muestran todos los bloques con avance 0%."
        )

    # -----------------------------------------------------
    # Capa GeoJSON
    # -----------------------------------------------------
    layer = pdk.Layer(
        "GeoJsonLayer",
        data=geojson,
        filled=True,
        get_fill_color="properties.color",
        stroked=True,
        get_line_color=[60, 60, 60, 255],
        line_width_min_pixels=1,
        pickable=True,
        auto_highlight=True,
    )

    view_state = pdk.ViewState(
        latitude=45.2,
        longitude=8.44,
        zoom=6.5
    )

    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style=None,
        views=[pdk.View(type="MapView", controller=True)],
        tooltip={
            "html": """
            <b>Zona:</b> {Asignacion}{BLOQUE}<br/>
            <b>Asignación:</b> {Asignacion}<br/>
            <b>Bloque:</b> {BLOQUE}<br/>
            <b>Operador:</b> {operador}
            """,
            "style": {
                "backgroundColor": "#333",
                "color": "white"
            }
        }
    )

    st.pydeck_chart(deck, use_container_width=True)
