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
    - complejidad

    La región se selecciona en pantalla y se aplica a todo el archivo.
    """)

    # ============================
    # CONEXIÓN LIMPIA
    # ============================
    conn = get_connection()
    conn.rollback()  # 🔥 limpia transacciones abortadas previas
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
        st.warning("Debe indicar una región antes de continuar")
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

    # ============================
    # LECTURA
    # ============================
    try:
        df = pd.read_csv(archivo)
    except Exception:
        df = pd.read_excel(archivo)

    df.columns = df.columns.str.lower().str.strip()

    columnas_requeridas = {"asignacion", "bloque", "complejidad"}
    if not columnas_requeridas.issubset(df.columns):
        st.error("❌ El archivo debe tener las columnas: asignacion, bloque y complejidad")
        st.stop()

    # ============================
    # LIMPIEZA DE DATOS
    # ============================
    df["asignacion"] = df["asignacion"].astype(str).str.strip()
    df["complejidad"] = df["complejidad"].astype(str).str.strip()

    st.subheader("📄 Vista previa")
    st.dataframe(df, width="stretch")

    # ============================
    # CARGA OPTIMIZADA
    # ============================
    if st.button("🚀 Cargar asignaciones"):
        total = len(df)
        progress = st.progress(0)
        status = st.empty()

        registros = []
        errores = []

        with st.spinner("⏳ Procesando archivo..."):
            for i, (_, row) in enumerate(df.iterrows(), start=1):
                try:
                    bloque = int(row["bloque"])

                    registros.append((
                        region_sel,
                        row["asignacion"],
                        bloque,
                        row["complejidad"]
                    ))

                except Exception as e:
                    errores.append(f"Fila {i}: {e}")

                progress.progress(i / total)
                status.text(f"Preparando fila {i} de {total}")

            try:
                cur.executemany("""
                    INSERT INTO asignaciones (
                        region,
                        asignacion,
                        bloque,
                        complejidad
                    )
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (region, asignacion, bloque) DO NOTHING
                """, registros)

                conn.commit()

                insertados = cur.rowcount
                omitidos = total - insertados

            except Exception as e:
                conn.rollback()
                st.error("❌ Error al insertar en la base de datos")
                st.exception(e)
                return

        st.success(f"""
        ✅ Carga finalizada  
        🌍 Región: {region_sel}  
        ➕ Insertados: {insertados}  
        ⏭️ Omitidos: {omitidos}
        """)

        if errores:
            with st.expander("⚠️ Filas con error de formato"):
                for err in errores[:20]:
                    st.text(err)

