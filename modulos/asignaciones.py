import streamlit as st
import pandas as pd
from db import get_connection
from permisos import validar_acceso


def render():
    # =========================
    # Control de acceso
    # =========================
    validar_acceso("Asignación de Producción")

    usuario = st.session_state["usuario"]
    cedula = usuario["cedula"]
    puesto = usuario["puesto"]

    conn = get_connection()

    # =========================
    # Mensaje persistente
    # =========================
    if "msg_ok" not in st.session_state:
        st.session_state.msg_ok = False

    st.title("📍 Módulo de Asignaciones")

    if st.session_state.msg_ok:
        st.success("✅ Cambios guardados correctamente")
        st.session_state.msg_ok = False

    # =====================================================
    # ======================= OPERADOR ====================
    # =====================================================
    if puesto != "Operario Catastral CC":
        st.subheader("👷 Operativo")

        # ---------------------------------
        # Autoasignación
        # ---------------------------------
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
                        proceso_actual = 'operativo',
                        operador_actual = %s
                    WHERE id = %s
                """, (cedula, aid))

                cur.execute("""
                    INSERT INTO asignaciones_historial
                    (asignacion_id, asignacion, bloque, usuario, puesto, proceso, estado)
                    VALUES (%s,%s,%s,%s,%s,'operativo','asignado')
                """, (aid, asig, blo, cedula, puesto))

                conn.commit()
                st.session_state.msg_ok = True
                st.rerun()
            else:
                st.info("No hay bloques pendientes")

        # ---------------------------------
        # Tabla operador
        # ---------------------------------
        df = pd.read_sql("""
            SELECT id, asignacion, bloque, estado_actual
            FROM asignaciones
            WHERE operador_actual = %s
            ORDER BY asignacion, bloque
        """, conn, params=(cedula,))

        if not df.empty:
            df_editable = df[df["estado_actual"] != "finalizado"]
            df_bloqueado = df[df["estado_actual"] == "finalizado"]

            # -------- Editables --------
            if not df_editable.empty:
                st.subheader("✏️ Bloques en edición")

                df_edit = st.data_editor(
                    df_editable,
                    disabled=["id", "asignacion", "bloque"],
                    column_config={
                        "estado_actual": st.column_config.SelectboxColumn(
                            "Estado",
                            options=["asignado", "proceso", "finalizado"]
                        )
                    },
                    use_container_width=True
                )

                if st.button("💾 Guardar cambios"):
                    cur = conn.cursor()

                    for _, r in df_edit.iterrows():
                        asignacion_id = int(r["id"])
                        nuevo_estado = r["estado_actual"]

                        cur.execute("""
                            SELECT estado_actual, asignacion, bloque
                            FROM asignaciones
                            WHERE id = %s
                        """, (asignacion_id,))

                        estado_bd, asignacion, bloque = cur.fetchone()

                        if estado_bd != nuevo_estado:
                            cur.execute("""
                                UPDATE asignaciones
                                SET estado_actual = %s
                                WHERE id = %s
                            """, (nuevo_estado, asignacion_id))

                            cur.execute("""
                                INSERT INTO asignaciones_historial
                                (asignacion_id, asignacion, bloque, usuario, puesto, proceso, estado)
                                VALUES (%s,%s,%s,%s,%s,'operativo',%s)
                            """, (
                                asignacion_id,
                                asignacion,
                                bloque,
                                cedula,
                                puesto,
                                nuevo_estado
                            ))

                    conn.commit()
                    st.session_state.msg_ok = True
                    st.rerun()

            # -------- Bloqueados --------
            if not df_bloqueado.empty:
                st.subheader("🔒 Bloques finalizados (solo lectura)")
                st.dataframe(df_bloqueado, use_container_width=True)

        # ---------------------------------
        # Rechazos
        # ---------------------------------
        st.subheader("❌ Rechazos pendientes")

        df_rech = pd.read_sql("""
            SELECT id, asignacion, bloque, estado_actual
            FROM asignaciones
            WHERE operador_actual = %s
              AND estado_actual LIKE 'rechazado%%'
            ORDER BY asignacion, bloque
        """, conn, params=(cedula,))

        if not df_rech.empty:
            st.dataframe(df_rech, use_container_width=True)

            if st.button("🔁 Marcar correcciones y enviar a QC"):
                cur = conn.cursor()

                for _, r in df_rech.iterrows():
                    cur.execute("""
                        UPDATE asignaciones
                        SET proceso_actual = 'control_calidad'
                        WHERE id = %s
                    """, (int(r["id"]),))

                    cur.execute("""
                        INSERT INTO asignaciones_historial
                        (asignacion_id, proceso, estado, usuario, puesto)
                        VALUES (%s,'operativo','corregido',%s,%s)
                    """, (int(r["id"]), cedula, puesto))

                conn.commit()
                st.session_state.msg_ok = True
                st.rerun()

    # =====================================================
    # ================= CONTROL DE CALIDAD ================
    # =====================================================
    else:
        st.subheader("🧪 Control de Calidad")

        # ---------------------------------
        # Autoasignación QC
        # ---------------------------------
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

                cur.execute("""
                    INSERT INTO asignaciones_historial
                    (asignacion_id, asignacion, bloque, usuario, puesto, proceso, estado)
                    VALUES (%s,%s,%s,%s,%s,'control_calidad','pendiente')
                """, (aid, asig, blo, cedula, puesto))

                conn.commit()
                st.session_state.msg_ok = True
                st.rerun()
            else:
                st.info("No hay bloques finalizados")

        # ---------------------------------
        # Tabla QC
        # ---------------------------------
        df_qc = pd.read_sql("""
            SELECT id, asignacion, bloque, estado_actual
            FROM asignaciones
            WHERE qc_actual = %s
            ORDER BY asignacion, bloque
        """, conn, params=(cedula,))

        if df_qc.empty:
            return

        df_edit = st.data_editor(
            df_qc,
            disabled=["id", "asignacion", "bloque"],
            column_config={
                "estado_actual": st.column_config.SelectboxColumn(
                    "Estado",
                    options=["pendiente", "aprobado", "rechazado"]
                )
            },
            use_container_width=True
        )

        observacion = st.text_area("Observación de rechazo (opcional)")

        # ---------------------------------
        # Guardar revisión QC
        # ---------------------------------
        if st.button("💾 Guardar revisión"):
            cur = conn.cursor()

            for _, r in df_edit.iterrows():
                asignacion_id = int(r["id"])
                estado = r["estado_actual"]

                if estado == "pendiente":
                    continue

                if estado == "aprobado":
                    cur.execute("""
                        UPDATE asignaciones
                        SET estado_actual = 'aprobado',
                            cantidad_aprobaciones = cantidad_aprobaciones + 1
                        WHERE id = %s
                    """, (asignacion_id,))

                    cur.execute("""
                        INSERT INTO asignaciones_historial
                        (asignacion_id, proceso, estado, usuario, puesto)
                        VALUES (%s,'control_calidad','aprobado',%s,%s)
                    """, (asignacion_id, cedula, puesto))

                elif estado == "rechazado":
                    cur.execute("""
                        UPDATE asignaciones
                        SET cantidad_rechazos = cantidad_rechazos + 1,
                            estado_actual = 'rechazado ' || (cantidad_rechazos + 1),
                            proceso_actual = 'operativo'
                        WHERE id = %s
                    """, (asignacion_id,))

                    cur.execute("""
                        INSERT INTO asignaciones_historial
                        (asignacion_id, proceso, estado, usuario, puesto, observacion)
                        VALUES (%s,'control_calidad','rechazado',%s,%s,%s)
                    """, (asignacion_id, cedula, puesto, observacion))

            conn.commit()
            st.session_state.msg_ok = True
            st.rerun()

