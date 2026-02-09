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
    # C) EVENTOS POR CATEGORÍA
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
    # D) MAPA – AVANCE POR BLOQUES
    # =====================================================
    st.subheader("🗺️ Avance por bloques")

    # -------- Regiones --------
    df_regiones = pd.read_sql("""
        SELECT DISTINCT region
        FROM reportes
        WHERE tipo_reporte = 'produccion'
          AND region IS NOT NULL
        ORDER BY region
    """, conn)

    lista_regiones = ["Todas"] + df_regiones["region"].tolist()

    col1, col2, col3 = st.columns(3)
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
    with col3:
        region_seleccionada = st.selectbox(
            "Región",
            options=lista_regiones
        )

    # -------- Consulta zonas --------
    where_region = ""
    params = [fecha_ini_map, fecha_fin_map]

    if region_seleccionada != "Todas":
        where_region = " AND r.region = %s"
        params.append(region_seleccionada)

    df_zonas = pd.read_sql(f"""
        SELECT
            r.zona,
            p.nombre_completo AS operador
        FROM reportes r
        JOIN personal p ON p.cedula = r.cedula_personal
        WHERE r.tipo_reporte = 'produccion'
          AND r.zona IS NOT NULL
          AND r.fecha_reporte BETWEEN %s AND %s
          {where_region}
    """, conn, params=params)

    zona_operadores = {}

    for _, row in df_zonas.iterrows():
        zona = row["zona"].strip()
        operador = row["operador"]
        zona_operadores.setdefault(zona, set()).add(operador)

    zonas_reportadas = set(zona_operadores.keys())

    # -------- GeoJSON --------
    with open("italia.geojson", "r", encoding="utf-8") as f:
        geojson = json.load(f)

    for feature in geojson["features"]:
        asignacion = str(feature["properties"]["Asignacion"]).strip()
        bloque = normalizar_bloque(feature["properties"]["BLOQUE"])
        region_geo = str(feature["properties"]["region"]).strip()

        zona = f"{asignacion}{bloque}"

        if (
            zona in zonas_reportadas and
            (region_seleccionada == "Todas" or region_geo == region_seleccionada)
        ):
            feature["properties"]["color"] = [31, 119, 255, 180]
            feature["properties"]["operador"] = ", ".join(
                sorted(zona_operadores.get(zona, []))
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
            <b>Región:</b> {region}<br/>
            <b>Operador:</b> {operador}
            """,
            "style": {"backgroundColor": "#333", "color": "white"}
        }
    )

    st.pydeck_chart(deck, use_container_width=True)

    # =====================================================
    # TABLA – DETALLE DE BLOQUES (MISMO FILTRO DEL MAPA)
    # =====================================================
    st.subheader("📋 Detalle de avance por bloque")

    params_tabla = [fecha_ini_map, fecha_fin_map]
    where_region = ""

    if region_seleccionada != "Todas":
        where_region = " AND r.region = %s"
        params_tabla.append(region_seleccionada)

    df_tabla = pd.read_sql(f"""
        SELECT
            SUBSTRING(r.zona FROM 1 FOR LENGTH(r.zona) - 3) AS asignacion,
            RIGHT(r.zona, 3) AS bloque,
            p.nombre_completo AS operador,
            COUNT(r.id) AS cantidad_reportes
        FROM reportes r
        JOIN personal p ON p.cedula = r.cedula_personal
        WHERE r.tipo_reporte = 'produccion'
          AND r.fecha_reporte BETWEEN %s AND %s
          {where_region}
        GROUP BY asignacion, bloque, p.nombre_completo
        ORDER BY asignacion, bloque, operador
    """, conn, params=params_tabla)

    if df_tabla.empty:
        st.info("No hay información de bloques para los filtros seleccionados.")
    else:
        df_tabla["estado"] = df_tabla["cantidad_reportes"].apply(
            lambda x: "🟦 Avanzado" if x > 0 else "⬜ Sin avance"
        )

        st.dataframe(
            df_tabla[["asignacion", "bloque", "operador", "estado"]],
            use_container_width=True,
            hide_index=True
        )
