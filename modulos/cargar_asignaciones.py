import streamlit as st
import pandas as pd
from db import get_connection
from permisos import validar_acceso


def render():
    validar_acceso("Cargar Asignaciones")

    usuario = st.session_state["usuario"]
    puesto = usuario["puesto"]

    if puesto not in ("Supervisor", "Coordinador", "Streamlit/pruebas"):
        st.error("⛔ Solo Supervisor o Coordinador puede cargar asignaciones")
        st.stop()

    st.title("📥 Cargar Asignaciones desde Excel / CSV")

    st.info("""
    El archivo debe contener:
    - asignacion
    - bloque
    - complejidad
    """)

    # ============================
    # CONEXIÓN (LIMPIA)
    # ============================
    conn = get_connection()
    conn.rollback()          # 🔥 limpia transacciones fallidas previas
    cur = conn.cursor()

    # ============================
    # REGIÓN
    # ============================
    cur.execute("""
        SELECT DISTINCT region
        FROM asignaciones
        WHERE region IS NOT NULL
        ORDER BY region
    """)
    regiones = [r[0] for r in cur.fetchall()]

    region_sel = st.selectbox(
        "🌍 Región",
        regiones + ["➕ Nueva región"]
    )

    if region_sel == "➕ Nueva región":
        region_sel = st.text_input("Ingrese nueva región").strip()

    if not region_sel:
        st.warning("Debe indicar una región")
        return

    st.divider()

    # ============================
    # ARCHIVO
    # ============================
    archivo = st.file_uploader(
        "Seleccione archivo CSV o Excel",
        type=["csv", "xlsx"]
    )

    if not archivo:
        return

    try:
        df = pd.read_csv(archivo)
    except Exception:
        df = pd.read_excel(archivo)

    df.columns = df.columns.str.lower().str.strip()

    if not {"asignacion", "bloque", "complejidad"}.issubset(df.columns):
        st.error("❌ El archivo debe tener asignacion, bloque y complejidad")
        st.stop()

    # Limpieza
    df["asignacion"] = df["asignacion"].astype(str).str.strip()
    df["complejidad"] = df["complejidad"].astype(str).str.strip()

    st.subheader("📄 Vista previa")
    st.dataframe(df, width="stretch")

    # ============================
    # CARGA
    # ============================
    if st.button("🚀 Cargar asignaciones"):
        total = len(df)
        insertados = 0
        omitidos = 0
        errores = []

        progress = st.progress(0)
        status = st.empty()

        with st.spinner("⏳ Procesando archivo..."):
            for i, (_, row) in enumerate(df.iterrows(), start=1):
                try:
                    status.text(f"Procesando fila {i} de {total}")

                    bloque = int(row["bloque"])

                    cur.execute("""
                        INSERT INTO asignaciones (
                            region,
                            asignacion,
                            bloque,
                            complejidad
                        )
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (region, asignacion, bloque) DO NOTHING
                    """, (
                        region_sel,
                        row["asignacion"],
                        bloque,
                        row["complejidad"]
                    ))

                    conn.commit()

                    if cur.rowcount > 0:
                        insertados += 1
                    else:
                        omitidos += 1

                except Exception as e:
                    conn.rollback()
                    omitidos += 1
                    errores.append(f"Fila {i}: {e}")

                progress.progress(i / total)

        st.success(f"""
        ✅ Carga finalizada  
        🌍 Región: {region_sel}  
        ➕ Insertados: {insertados}  
        ⏭️ Omitidos: {omitidos}
        """)

        if errores:
            with st.expander("⚠️ Ver errores detectados"):
                for err in errores[:20]:
                    st.text(err)

