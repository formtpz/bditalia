import streamlit as st
import pandas as pd
from db import get_connection
from permisos import validar_acceso


def render():
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
        st.success("✅ Cambio guardado correctamente")
        st.session_state.msg_ok = False

    # =====================================================
    # ======================= OPERADOR ====================
    # =====================================================
    if puesto != "Operario Catastral CC":
        st.subheader("👷 Operativo")

        # ---------- AUTOASIGNACIÓN POR ASIGNACIÓN ----------
        if st.button("🧲 Autoasignarme una asignación completa"):
            cur = conn.cursor()

            cur.execute("""
                SELECT asignacion
                FROM asignaciones
                WHERE estado_actual = 'pendiente'
                GROUP BY asignacion
                ORDER BY asignacion
                LIMIT 1
            """)
            row = cur.fetchone()

            if not row:
                st.info("No hay asignaciones pendientes")
            else:
                asignacion_sel = row[0]

                cur.execute("""
                    UPDATE asignaciones
                    SET operador_actual = %s,
                        proceso_actual = 'operativo',
                        estado_actual = 'asignado'
                    WHERE asignacion = %s
                      AND estado_actual = 'pendiente'
                """, (cedula, asignacion_sel))

                cur.execute("""
                    INSERT INTO asignaciones_historial
                    (asignacion_id, asignacion, bloque, usuario, puesto, proceso, estado)
                    SELECT id, asignacion, bloque, %s, %s, 'operativo', 'asignado'
                    FROM asignaciones
                    WHERE asignacion = %s
                """, (cedula, puesto, asignacion_sel))


                conn.commit()
                st.session_state.msg_ok = True
                st.rerun()

        # ---------- TABLA SOLO LECTURA ----------
        filtro = st.selectbox(
            "Filtrar por estado",
            ["Todos", "pendiente", "asignado", "proceso", "finalizado"]
        )

        where = ""
        params = [cedula]

        if filtro != "Todos":
            where = " AND estado_actual = %s"
            params.append(filtro)

        df = pd.read_sql(
            f"""
            SELECT asignacion, bloque, estado_actual
            FROM asignaciones
            WHERE operador_actual = %s
            {where}
            ORDER BY asignacion, bloque
            """,
            conn,
            params=tuple(params)
        )

        st.dataframe(df, use_container_width=True)

        # ---------- SELECCIÓN PUNTUAL ----------
        opciones = df[df["estado_actual"] != "finalizado"].copy()
        opciones["label"] = opciones["asignacion"] + " - Bloque " + opciones["bloque"].astype(str)

        if opciones.empty:
            return

        seleccionado = st.selectbox(
            "Seleccione bloque a trabajar",
            opciones["label"]
        )

        fila = opciones[opciones["label"] == seleccionado].iloc[0]

        nuevo_estado = st.selectbox(
            "Nuevo estado",
            ["asignado", "proceso", "finalizado"]
        )

        if st.button("💾 Guardar cambio"):
            cur = conn.cursor()

            cur.execute("""
                UPDATE asignaciones
                SET estado_actual = %s
                WHERE asignacion = %s
                  AND bloque = %s
            """, (nuevo_estado, fila["asignacion"], int(fila["bloque"])))

            cur.execute("""
                INSERT INTO asignaciones_historial
                (asignacion, bloque, usuario, puesto, proceso, estado)
                VALUES (%s,%s,%s,%s,'operativo',%s)
            """, (
                fila["asignacion"],
                int(fila["bloque"]),
                cedula,
                puesto,
                nuevo_estado
            ))

            conn.commit()
            st.session_state.msg_ok = True
            st.rerun()

    # =====================================================
    # ================= CONTROL DE CALIDAD ================
    # =====================================================
    else:
        st.subheader("🧪 Control de Calidad")

        # ---------- AUTOASIGNACIÓN QC ----------
        if st.button("🧲 Autoasignar una asignación para QC"):
            cur = conn.cursor()

            cur.execute("""
                SELECT asignacion
                FROM asignaciones
                GROUP BY asignacion
                HAVING COUNT(*) = COUNT(
                    CASE WHEN estado_actual = 'finalizado' THEN 1 END
                )
                ORDER BY asignacion
                LIMIT 1
            """)
            row = cur.fetchone()

            if not row:
                st.info("No hay asignaciones listas para QC")
            else:
                asignacion_sel = row[0]

                cur.execute("""
                    UPDATE asignaciones
                    SET qc_actual = %s,
                        proceso_actual = 'control_calidad',
                        estado_actual = 'pendiente'
                    WHERE asignacion = %s
                """, (cedula, asignacion_sel))

                cur.execute("""
                    INSERT INTO asignaciones_historial
                    (asignacion_id, asignacion, usuario, puesto, proceso, estado)
                    SELECT id, asignacion, %s, %s, 'control_calidad', 'pendiente'
                    FROM asignaciones
                    WHERE asignacion = %s
                """, (cedula, puesto, asignacion_sel))

                conn.commit()
                st.session_state.msg_ok = True
                st.rerun()

        # ---------- TABLA SOLO LECTURA ----------
        filtro = st.selectbox(
            "Filtrar por estado",
            ["Todos", "pendiente", "rechazado", "aprobado"]
        )

        where = ""
        params = [cedula]

        if filtro != "Todos":
            where = " AND estado_actual LIKE %s"
            params.append(f"%{filtro}%")

        df = pd.read_sql(
            f"""
            SELECT asignacion, bloque, estado_actual
            FROM asignaciones
            WHERE qc_actual = %s
            {where}
            ORDER BY asignacion, bloque
            """,
            conn,
            params=tuple(params)
        )

        st.dataframe(df, use_container_width=True)

        # ---------- SELECCIÓN PUNTUAL ----------
        opciones = df[~df["estado_actual"].str.contains("aprobado")].copy()
        opciones["label"] = opciones["asignacion"] + " - Bloque " + opciones["bloque"].astype(str)

        if opciones.empty:
            return

        seleccionado = st.selectbox(
            "Seleccione bloque a revisar",
            opciones["label"]
        )

        fila = opciones[opciones["label"] == seleccionado].iloc[0]

        nuevo_estado = st.selectbox(
            "Resultado QC",
            ["pendiente", "aprobado", "rechazado"]
        )

        observacion = st.text_area("Observación (solo si rechaza)")

        if st.button("💾 Guardar revisión"):
            cur = conn.cursor()

            if nuevo_estado == "aprobado":
                cur.execute("""
                    UPDATE asignaciones
                    SET estado_actual = 'aprobado'
                    WHERE asignacion = %s
                      AND bloque = %s
                """, (fila["asignacion"], int(fila["bloque"])))

            elif nuevo_estado == "rechazado":
                cur.execute("""
                    UPDATE asignaciones
                    SET estado_actual = 'rechazado',
                        proceso_actual = 'operativo'
                    WHERE asignacion = %s
                      AND bloque = %s
                """, (fila["asignacion"], int(fila["bloque"])))

            cur.execute("""
                INSERT INTO asignaciones_historial
                (asignacion, bloque, usuario, puesto, proceso, estado, observacion)
                VALUES (%s,%s,%s,%s,'control_calidad',%s,%s)
            """, (
                fila["asignacion"],
                int(fila["bloque"]),
                cedula,
                puesto,
                nuevo_estado,
                observacion
            ))

            conn.commit()
            st.session_state.msg_ok = True
            st.rerun()

