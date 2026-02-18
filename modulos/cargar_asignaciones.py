import streamlit as st
import pandas as pd
from db import get_connection
from permisos import validar_acceso


def render():
    validar_acceso("Cargar Asignaciones")

    usuario = st.session_state["usuario"]
    puesto = usuario["puesto"]
    cedula = usuario["cedula"]

    if puesto not in ("Supervisor", "Coordinador", "Streamlit/pruebas"):
        st.error("⛔ Solo Supervisor o Coordinador puede cargar asignaciones")
        st.stop()

    st.title("📥 Cargar Asignaciones desde Excel / CSV")

    st.info("""
    El archivo debe contener:
    - asignacion
    - bloque
    - complejidad

    La región se selecciona en pantalla.
    """)

    # ============================
    # CONEXIÓN LIMPIA
    # ============================
    conn = get_connection()
    conn.rollback()
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

    region_sel = st.selectbox("🌍 Región", regiones + ["➕ Nueva región"])

    if region_sel == "➕ Nueva región":
        region_sel = st.text_input("Ingrese nueva región").strip()

    if not region_sel:
        st.warning("Debe indicar una región")
        return

    # =====================================================
    # 🔄 DESASIGNAR ASIGNACIÓN COMPLETA (NUEVO BLOQUE)
    # =====================================================
    st.divider()
    st.subheader("🔄 Desasignar asignación completa")

    cur.execute("""
        SELECT asignacion
        FROM asignaciones
        WHERE region = %s
        GROUP BY asignacion
        HAVING COUNT(DISTINCT estado_actual) = 1
           AND MAX(estado_actual) = 'asignado'
        ORDER BY asignacion
    """, (region_sel,))

    asignaciones_des = [row[0] for row in cur.fetchall()]

    if not asignaciones_des:
        st.info("No hay asignaciones completamente en estado 'asignado'")
    else:
        asignacion_sel = st.selectbox(
            "Seleccione asignación a devolver a pendiente según la Región preseleccionada",
            asignaciones_des
        )

        confirmar = st.checkbox(
            "Confirmo que deseo desasignar esta asignación completa"
        )

        if confirmar:
            if st.button("🚨 Desasignar"):

                try:
                    cur.execute("""
                        UPDATE asignaciones
                        SET operador_actual = NULL,
                            estado_actual = 'pendiente'
                        WHERE asignacion = %s
                          AND region = %s
                    """, (asignacion_sel, region_sel))

                    conn.commit()

                    st.success("✅ Asignación devuelta a pendiente correctamente")
                    st.rerun()

                except Exception as e:
                    conn.rollback()
                    st.error("❌ Error al desasignar")
                    st.exception(e)

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

    # ============================
    # LIMPIEZA
    # ============================
    df["asignacion"] = df["asignacion"].astype(str).str.strip()
    df["bloque"] = df["bloque"].astype(int)
    df["complejidad"] = df["complejidad"].astype(str).str.strip()

    # ============================
    # 1️⃣ ELIMINAR DUPLICADOS EN EL ARCHIVO
    # ============================
    df = df.drop_duplicates(subset=["asignacion", "bloque"])

    st.subheader("📄 Vista previa (sin duplicados)")
    st.dataframe(df, width="stretch")

    # ============================
    # CARGA
    # ============================
    if st.button("🚀 Cargar asignaciones"):
        with st.spinner("⏳ Procesando archivo..."):

            # ============================
            # 2️⃣ CONSULTAR EXISTENTES EN BD
            # ============================
            cur.execute("""
                SELECT asignacion, bloque
                FROM asignaciones
                WHERE region = %s
            """, (region_sel,))

            existentes = set(cur.fetchall())

            # ============================
            # 3️⃣ FILTRAR SOLO NUEVOS
            # ============================
            nuevos = []
            omitidos = 0

            for _, row in df.iterrows():
                key = (row["asignacion"], row["bloque"])
                if key in existentes:
                    omitidos += 1
                else:
                    nuevos.append((
                        region_sel,
                        row["asignacion"],
                        row["bloque"],
                        row["complejidad"]
                    ))

            if not nuevos:
                st.info("No hay nuevas asignaciones para insertar")
                return

            # ============================
            # 4️⃣ INSERTAR (SIN ON CONFLICT)
            # ============================
            try:
                cur.executemany("""
                    INSERT INTO asignaciones (
                        region,
                        asignacion,
                        bloque,
                        complejidad
                    )
                    VALUES (%s, %s, %s, %s)
                """, nuevos)

                conn.commit()

            except Exception as e:
                conn.rollback()
                st.error("❌ Error al insertar en la base de datos")
                st.exception(e)
                return

        st.success(f"""
        ✅ Carga finalizada  
        🌍 Región: {region_sel}  
        ➕ Insertados: {len(nuevos)}  
        ⏭️ Omitidos (ya existentes): {omitidos}
        """)
