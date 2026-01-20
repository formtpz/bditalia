import streamlit as st
import pandas as pd
from datetime import datetime
from db import get_connection
from permisos import validar_acceso


def render():
    validar_acceso("Correcciones")

    usuario = st.session_state["usuario"]
    perfil = usuario["perfil"]

    conn = get_connection()

    st.title("🛠️ Correcciones de Reportes")

    # =====================================================
    # PERFIL 3 → SOLICITUD
    # =====================================================
    if perfil == 3:
        st.subheader("✏️ Solicitar corrección")

        columnas_reportes = [
            "fecha_reporte",
            "horas",
            "zona",
            "produccion",
            "aprobados",
            "rechazados",
            "observaciones"
        ]

        with st.form("form_solicitud"):
            id_asociado = st.text_input("ID del reporte")
            columna = st.selectbox("Columna con error", columnas_reportes)
            nuevo_valor = st.text_input("Nuevo valor correcto")

            solucion = st.selectbox(
                "Tipo de acción",
                ["MODIFICAR", "ELIMINAR"]
            )

            detalle = st.text_area("Detalle del error")

            submit = st.form_submit_button("Enviar solicitud")

        if submit:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO correcciones (
                    cedula, nombre, fecha, id_asociado,
                    tipo_error, solucion, tabla,
                    columna, nuevo_valor, estado
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                usuario["cedula"],
                usuario["nombre"],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                id_asociado,
                columna,
                solucion,
                "reportes",
                columna,
                nuevo_valor,
                "pendiente"
            ))
            conn.commit()
            st.success("✅ Solicitud registrada")

        st.divider()

        st.subheader("📜 Mis solicitudes")
        df = pd.read_sql("""
            SELECT fecha, id_asociado, columna, solucion, estado
            FROM correcciones
            WHERE cedula = %s
            ORDER BY fecha DESC
        """, conn, params=[usuario["cedula"]])

        st.dataframe(df, use_container_width=True)

    # =====================================================
    # PERFIL 1 → APLICAR CORRECCIONES
    # =====================================================
    elif perfil == 1:
        st.subheader("📥 Correcciones pendientes")

        df_corr = pd.read_sql("""
            SELECT *
            FROM correcciones
            WHERE estado = 'pendiente'
            ORDER BY fecha
        """, conn)

        if df_corr.empty:
            st.info("No hay correcciones pendientes")
            return

        seleccion = st.selectbox(
            "Seleccione una corrección",
            df_corr["id"]
        )

        corr = df_corr[df_corr["id"] == seleccion].iloc[0]
        id_reporte = corr["id_asociado"]

        st.markdown("### 🧾 Reporte asociado")

        df_rep = pd.read_sql("""
            SELECT *
            FROM reportes
            WHERE id = %s
        """, conn, params=[id_reporte])

        if df_rep.empty:
            st.error("Reporte no encontrado")
            return

        reporte = df_rep.iloc[0]

        with st.form("editar_reporte"):
            campos_editables = {}

            for col in df_rep.columns:
                if col in ("id",):
                    st.text_input(col, value=reporte[col], disabled=True)
                else:
                    campos_editables[col] = st.text_input(
                        col,
                        value=str(reporte[col]) if reporte[col] is not None else ""
                    )

            guardar_rep = st.form_submit_button("💾 Guardar cambios en reportes")

        if guardar_rep:
            set_clause = ", ".join([f"{k} = %s" for k in campos_editables])
            valores = list(campos_editables.values())
            valores.append(id_reporte)

            cur = conn.cursor()
            cur.execute(
                f"UPDATE reportes SET {set_clause} WHERE id = %s",
                valores
            )
            conn.commit()
            st.success("✅ Reporte actualizado")

        st.divider()

        if st.button("✔ Marcar corrección como CORREGIDA"):
            cur = conn.cursor()
            cur.execute("""
                UPDATE correcciones
                SET estado = 'corregido'
                WHERE id = %s
            """, (seleccion,))
            conn.commit()
            st.success("✅ Corrección cerrada")
            st.rerun()
