import streamlit as st
import pandas as pd
from db import get_connection
from permisos import validar_acceso


def render():
    validar_acceso("Cargar Asignaciones")

    usuario = st.session_state["usuario"]
    puesto = usuario["puesto"]

    # ============================
    # RESTRICCIÓN DE ACCESO
    # ============================
    if puesto not in ("Supervisor", "Coordinador", "Streamlit/pruebas"):
        st.error("⛔ Solo Supervisor o Coordinador puede cargar asignaciones")
        st.stop()

    st.title("📥 Cargar Asignaciones desde Excel / CSV")

    st.info("""
    El archivo debe contener las columnas:
    - asignacion
    - bloque

    La región se selecciona antes de la carga y se aplica a todo el archivo.
    """)

    # ============================
    # SELECCIÓN DE REGIÓN
    # ============================
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT region
        FROM asignaciones
        WHERE region IS NOT NULL
        ORDER BY region
    """)
    regiones = [r[0] for r in cur.fetchall()]

    region_sel = st.selectbox(
        "🌍 Región de las asignaciones",
        regiones + ["➕ Nueva región"]
    )

    if region_sel == "➕ Nueva región":
        region_sel = st.text_input("Ingrese el nombre de la nueva región").strip()

    if not region_sel:
        st.warning("Debe indicar una región antes de continuar")
        return

    st.divider()

    # ============================
    # CARGA DE ARCHIVO
    # ============================
    archivo = st.file_uploader(
        "Seleccione archivo CSV o Excel",
        type=["csv", "xlsx"]
    )

    if not archivo:
        return

    # ============================
    # LEER ARCHIVO
    # ============================
    try:
        df = pd.read_csv(archivo, sep=None, engine="python")
    except Exception:
        df = pd.read_excel(archivo)

    df.columns = df.columns.str.lower().str.strip()

    if not {"asignacion", "bloque"}.issubset(df.columns):
        st.error("❌ El archivo debe tener las columnas: asignacion y bloque")
        st.stop()

    # Limpieza básica
    df["asignacion"] = df["asignacion"].astype(str).str.strip()
    df["bloque"] = df["bloque"].astype(int)

    st.subheader("📄 Vista previa")
    st.dataframe(df, use_container_width=True)

    # ============================
    # INSERTAR EN BD
    # ============================
    if st.button("🚀 Cargar asignaciones"):
        insertados = 0
        omitidos = 0

        for _, row in df.iterrows():
            try:
                cur.execute("""
                    INSERT INTO asignaciones (region, asignacion, bloque)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (region, asignacion, bloque) DO NOTHING
                """, (
                    region_sel,
                    row["asignacion"],
                    int(row["bloque"])
                ))

                if cur.rowcount > 0:
                    insertados += 1
                else:
                    omitidos += 1

            except Exception:
                omitidos += 1

        conn.commit()

        st.success(f"""
        ✅ Carga finalizada  
        🌍 Región: {region_sel}  
        ➕ Insertados: {insertados}  
        ⏭️ Omitidos (duplicados o error): {omitidos}
        """)

