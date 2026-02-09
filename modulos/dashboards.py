import streamlit as st
import pandas as pd
import json
import pydeck as pdk
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
        SELECT puesto, COUNT(*) AS cantidad
        FROM personal
        WHERE estado = 'activo'
        GROUP BY puesto
        ORDER BY puesto
    """, conn)

    total_personal = df_personal["cantidad"].sum()

    df_personal_resumen = pd.concat(
        [
            pd.DataFrame([{"puesto": "TOTAL", "cantidad": total_personal}]),
            df_personal
        ],
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
    # MAPA – AVANCE POR BLOQUES
    # =====================================================
    st.subheader("🗺️ Avance por bloques")

    # -------- Regiones (desde asignaciones) --------
    df_regiones = pd.read_sql("""
        SELECT DISTINCT region
        FROM asignaciones
        WHERE region IS NOT NULL
        ORDER BY region
    """, conn)

    lista_regiones = ["Todas"] + df_regiones["region"].tolist()

    col1, col2, col3 = st.columns(3)
    with col1:
        fecha_ini_map = st.date_input(
            "Desde (mapa)", value=fecha_inicio, key="map_ini"
        )
    with col2:
        fecha_fin_map = st.date_input(
            "Hasta (mapa)", value=fecha_fin, key="map_fin"
        )
    with col3:
        region_seleccionada = st.selectbox("Región", lista_regiones)

    # =====================================================
    # REPORTES → BLOQUES CON AVANCE REAL
    # =====================================================
    where_region = ""
    params = [fecha_ini_map, fecha_fin_map]

    if region_seleccionada != "Todas":
        where_region = " AND r.region = %s"
        params.append(region_seleccionada)

    df_reportes = pd.read_sql(f"""
        SELECT
            r.region,
            a.asignacion,
            a.bloque,
            p.nombre_completo
        FROM reportes r
        JOIN asignaciones a
            ON a.region = r.region
           AND a.asignacion = SUBSTRING(r.zona FROM 1 FOR LENGTH(r.zona) - 1)
           AND a.bloque = CAST(SUBSTRING(r.zona FROM LENGTH(r.zona) FOR 1) AS INTEGER)
        JOIN personal p ON p.cedula = r.cedula_personal
        WHERE r.tipo_reporte = 'produccion'
          AND r.fecha_reporte BETWEEN %s AND %s
          {where_region}
    """, conn, params=params)

    zonas_con_avance = set(
        (row["region"], row["asignacion"], int(row["bloque"]))
        for _, row in df_reportes.iterrows()
    )

    operadores_por_zona = {}
    for _, row in df_reportes.iterrows():
        key = (row["region"], row["asignacion"], int(row["bloque"]))
        operadores_por_zona.setdefault(key, set()).add(row["nombre_completo"])

    # =====================================================
    # GEOJSON
    # =====================================================
    with open("italia.geojson", "r", encoding="utf-8") as f:
        geojson = json.load(f)

    for feature in geojson["features"]:
        region_geo = str(feature["properties"]["region"]).strip()
        asignacion_geo = str(feature["properties"]["Asignacion"]).strip()
        bloque_geo = int(feature["properties"]["BLOQUE"])

        key = (region_geo, asignacion_geo, bloque_geo)

        if (
            key in zonas_con_avance and
            (region_seleccionada == "Todas" or region_geo == region_seleccionada)
        ):
            feature["properties"]["color"] = [31, 119, 255, 180]
            feature["properties"]["operador"] = ", ".join(
                sorted(operadores_por_zona.get(key, []))
            )
        else:
            feature["properties"]["color"] = [220, 220, 220, 140]
            feature["properties"]["operador"] = "—"

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

    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=pdk.ViewState(
            latitude=45.2,
            longitude=8.44,
            zoom=6.5
        ),
        map_style=None,
        views=[pdk.View(type="MapView", controller=True)],
        tooltip={
            "html": """
            <b>Región:</b> {region}<br/>
            <b>Asignación:</b> {Asignacion}<br/>
            <b>Bloque:</b> {BLOQUE}<br/>
            <b>Operador:</b> {operador}
            """,
            "style": {"backgroundColor": "#333", "color": "white"}
        }
    )

    st.pydeck_chart(deck, use_container_width=True)

    # =====================================================
    # TABLA – ESTADO ACTUAL (ASIGNACIONES)
    # =====================================================
    st.subheader("📋 Estado actual por bloque")

    where_region = ""
    params_tabla = []

    if region_seleccionada != "Todas":
        where_region = " WHERE a.region = %s"
        params_tabla.append(region_seleccionada)

    df_tabla = pd.read_sql(f"""
        SELECT
            a.region,
            a.asignacion,
            a.bloque,
            COALESCE(p.nombre_completo, '—') AS operador,
            a.estado_actual AS estado
        FROM asignaciones a
        LEFT JOIN personal p
            ON p.cedula = a.operador_actual
        {where_region}
        ORDER BY a.region, a.asignacion, a.bloque
    """, conn, params=params_tabla)

    if df_tabla.empty:
        st.info("No hay asignaciones registradas.")
    else:
        st.dataframe(
            df_tabla,
            use_container_width=True,
            hide_index=True
        )
