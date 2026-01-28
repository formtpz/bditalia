import streamlit as st
import pandas as pd
from db import get_connection
from permisos import validar_acceso

def render():
    validar_acceso("Producción")

    usuario = st.session_state["usuario"]
    cedula = usuario["cedula"]
    puesto = usuario["puesto"]

    conn = get_connection()
    st.title("Módulo Asignaciones")

    # =====================================================
    # OPERATIVO
    # =====================================================
    if puesto != "Operario Catastral CC":
        st.subheader("👷 Operativo")

        if st.button("🧲 Autoasignarme un bloque"):
            cur = conn.cursor()
            cur.execute("""
                SELECT id, asignacion, bloque
                FROM asignaciones
                WHERE estado_actual = 'pendiente'
                ORDER BY asignacion, bloque
                LIMIT 1
            """)
            row = cur.fetchone()

            if row:
                aid, asig, blo = row

                cur.execute("""
                    UPDATE asignaciones
                    SET estado_actual = 'asignado',
                        operador_actual = %s,
                        proceso_actual = 'operativo'
                    WHERE id = %s
                """, (cedula, aid))

                cur.execute("""
                    INSERT INTO asignaciones_historial
                    (asignacion_id, asignacion, bloque, usuario, puesto, proceso, estado)
                    VALUES (%s,%s,%s,%s,%s,'operativo','asignado')
                """, (aid, asig, blo, cedula, puesto))

                conn.commit()
                st.success("✅ Bloque asignado")
                st.rerun()
            else:
                st.info("No hay bloques pendientes")

        df = pd.read_sql("""
            SELECT id, asignacion, bloque, estado_actual
            FROM asignaciones
            WHERE operador_actual = %s
        """, conn, params=[cedula])

        if not df.empty:
            df_edit = st.data_editor(
                df,
                disabled=["id","asignacion","bloque"],
                column_config={
                    "estado_actual": st.column_config.SelectboxColumn(
                        "Estado",
                        options=["asignado","proceso","finalizado"]
                    )
                }
            )

            if st.button("💾 Guardar cambios"):
                cur = conn.cursor()
                for _, r in df_edit.iterrows():
                    cur.execute("""
                        UPDATE asignaciones
                        SET estado_actual = %s
                        WHERE id = %s
                    """, (r["estado_actual"], int(r["id"])))
                conn.commit()
                st.success("Cambios guardados")
                st.rerun()

    # =====================================================
    # CONTROL DE CALIDAD
    # =====================================================
    else:
        st.subheader("🧪 Control de Calidad")

        if st.button("🧲 Autoasignar revisión"):
            cur = conn.cursor()
            cur.execute("""
                SELECT id, asignacion, bloque
                FROM asignaciones
                WHERE estado_actual = 'finalizado'
                ORDER BY asignacion, bloque
                LIMIT 1
            """)
            row = cur.fetchone()

            if row:
                aid, asig, blo = row
                cur.execute("""
                    UPDATE asignaciones
                    SET proceso_actual = 'control_calidad',
                        qc_actual = %s,
                        estado_actual = 'pendiente'
                    WHERE id = %s
                """, (cedula, aid))

                conn.commit()
                st.success("Bloque asignado a QC")
                st.rerun()
            else:
                st.info("No hay bloques finalizados")

        df_qc = pd.read_sql("""
            SELECT id, asignacion, bloque, estado_actual
            FROM asignaciones
            WHERE qc_actual = %s
        """, conn, params=[cedula])

        if df_qc.empty:
            return

        df_edit = st.data_editor(
            df_qc,
            disabled=["id","asignacion","bloque"],
            column_config={
                "estado_actual": st.column_config.SelectboxColumn(
                    "Estado",
                    options=["pendiente","aprobado","rechazado"]
                )
            }
        )

        observacion = st.text_area("Observación (solo si rechaza)")

        if st.button("💾 Guardar revisión"):
            cur = conn.cursor()

            for _, r in df_edit.iterrows():
                estado = r["estado_actual"]
                aid = int(r["id"])

                # ---- PENDIENTE ----
                if estado == "pendiente":
                    continue

                # ---- APROBADO ----
                elif estado == "aprobado":
                    cur.execute("""
                        UPDATE asignaciones
                        SET estado_actual = 'aprobado',
                            cantidad_aprobaciones = cantidad_aprobaciones + 1
                        WHERE id = %s
                    """, (aid,))

                    cur.execute("""
                        INSERT INTO asignaciones_historial
                        (asignacion_id, proceso, estado, usuario, puesto, observacion)
                        VALUES (%s,'control_calidad','aprobado',%s,%s,NULL)
                    """, (aid, cedula, puesto))

                # ---- RECHAZADO ----
                elif estado == "rechazado":
                    cur.execute("""
                        UPDATE asignaciones
                        SET cantidad_rechazos = cantidad_rechazos + 1,
                            estado_actual = 'rechazado ' || (cantidad_rechazos + 1),
                            proceso_actual = 'operativo'
                        WHERE id = %s
                    """, (aid,))

                    cur.execute("""
                        INSERT INTO asignaciones_historial
                        (asignacion_id, proceso, estado, usuario, puesto, observacion)
                        VALUES (%s,'control_calidad','rechazado',%s,%s,%s)
                    """, (aid, cedula, puesto, observacion))

            conn.commit()
            st.success("✅ Revisión guardada")
            st.rerun()
