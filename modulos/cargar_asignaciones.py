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
    """)

    archivo = st.file_uploader(
        "Seleccione archivo CSV o Excel",
        type=["csv", "xlsx"]
    )

    if not archivo:
        return

    # ============================
    # LEER ARCHIVO
    # ============================
    if archivo.name.endswith(".csv"):
        df = pd.read_csv(archivo)
    else:
        df = pd.read_excel(archivo)

    df.columns = df.columns.str.lower().str.strip()

    if not {"asignacion", "bloque"}.issubset(df.columns):
        st.error("❌ El archivo debe tener las columnas asignacion y bloque")
        st.stop()

    st.subheader("📄 Vista previa")
    st.dataframe(df, use_container_width=True)

    if st.button("🚀 Cargar asignaciones"):
        conn = get_connection()
        cur = conn.cursor()

        insertados = 0
        omitidos = 0

        for _, row in df.iterrows():
            try:
                cur.execute("""
                    INSERT INTO asignaciones (asignacion, bloque)
                    VALUES (%s, %s)
                    ON CONFLICT (asignacion, bloque) DO NOTHING
                """, (
                    str(row["asignacion"]).strip(),
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
        ➕ Insertados: {insertados}  
        ⏭️ Omitidos (duplicados o error): {omitidos}
        """)
