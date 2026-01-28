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

        # ---------- AUTOASIGNACIÓN ----------
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
            ["Todos", "rechazado", "corregido", "asignado", "proceso", "finalizado"]
        )

        where = ""
        params = [cedula]
        if filtro != "Todos":
            where = " AND estado_actual LIKE %s"
            params.append(f"%{filtro}%")

        df = pd.read_sql(
            f"""
            SELECT asignacion, bloque, estado_actual,
                   cantidad_rechazos, cantidad_aprobaciones
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
        if opciones.empty:
            return

        opciones["label"] = opciones["asignacion"] + " - Bloque " + opciones["bloque"].astype(str)
        seleccionado = st.selectbox("Seleccione bloque a trabajar", opciones["label"])
        fila = opciones[opciones["label"] == seleccionado].iloc[0]

        estado_actual = fila["estado_actual"]

        if estado_actual.startswith("rechazado"):
            opciones_estado = ["corregido"]
        elif estado_actual == "asignado":
            opciones_estado = ["proceso"]
        elif estado_actual == "proceso":
            opciones_estado = ["finalizado"]
        else:
            opciones_estado = []

        if not opciones_estado:
            st.info("Este bloque no puede modificarse")
            return

        nuevo_estado = st.selectbox("Nuevo estado", opciones_estado)

        if st.button("💾 Guardar cambio"):
            cur = conn.cursor()

            if nuevo_estado == "corregido":
                cur.execute("""
                    UPDATE asignaciones
                    SET estado_actual = 'corregido',
                        proceso_actual = 'control_calidad'
                    WHERE asignacion = %s
                      AND bloque = %s
                """, (fila["asignacion"], int(fila["bloque"])))
            else:
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

                # NO pisamos estado_actual aquí
                cur.execute("""
                    UPDATE asignaciones
                    SET qc_actual = %s,
                        proceso_actual = 'control_calidad'
                    WHERE asignacion = %s
                """, (cedula, asignacion_sel))

                cur.execute("""
                    INSERT INTO asignaciones_historial
                    (asignacion_id, asignacion, bloque, usuario, puesto, proceso, estado)
                    SELECT id, asignacion, bloque, %s, %s, 'control_calidad', estado_actual
                    FROM asignaciones
                    WHERE asignacion = %s
                """, (cedula, puesto, asignacion_sel))

                conn.commit()
                st.session_state.msg_ok = True
                st.rerun()

        # ---------- TABLA SOLO LECTURA ----------
        df = pd.read_sql("""
            SELECT asignacion, bloque, estado_actual,
                   cantidad_rechazos, cantidad_aprobaciones
            FROM asignaciones
            WHERE qc_actual = %s
            ORDER BY asignacion, bloque
        """, conn, params=(cedula,))

        st.dataframe(df, use_container_width=True)

        # ---------- SELECCIÓN PUNTUAL ----------
        opciones = df[df["estado_actual"].isin(["pendiente", "corregido"])].copy()
        if opciones.empty:
            return

        opciones["label"] = opciones["asignacion"] + " - Bloque " + opciones["bloque"].astype(str)
        seleccionado = st.selectbox("Seleccione bloque a revisar", opciones["label"])
        fila = opciones[opciones["label"] == seleccionado].iloc[0]

        nuevo_estado = st.selectbox("Resultado QC", ["aprobado", "rechazado"])
        observacion = st.text_area("Observación (solo si rechaza)")

        if st.button("💾 Guardar revisión"):
            cur = conn.cursor()

            if nuevo_estado == "aprobado":
                # Incremento ATÓMICO
                cur.execute("""
                    UPDATE asignaciones
                    SET cantidad_aprobaciones = cantidad_aprobaciones + 1,
                        estado_actual = 'aprobado'
                    WHERE asignacion = %s
                      AND bloque = %s
                """, (fila["asignacion"], int(fila["bloque"])))

                estado_hist = "aprobado"

            else:
                # Incremento ATÓMICO
                cur.execute("""
                    UPDATE asignaciones
                    SET cantidad_rechazos = cantidad_rechazos + 1,
                        estado_actual = 'rechazado ' || (cantidad_rechazos + 1),
                        proceso_actual = 'operativo'
                    WHERE asignacion = %s
                      AND bloque = %s
                """, (fila["asignacion"], int(fila["bloque"])))

                # Obtener estado generado (rechazado X)
                cur.execute("""
                    SELECT estado_actual
                    FROM asignaciones
                    WHERE asignacion = %s
                      AND bloque = %s
                """, (fila["asignacion"], int(fila["bloque"])))

                estado_hist = cur.fetchone()[0]

            cur.execute("""
                INSERT INTO asignaciones_historial
                (asignacion, bloque, usuario, puesto, proceso, estado, observacion)
                VALUES (%s,%s,%s,%s,'control_calidad',%s,%s)
            """, (
                fila["asignacion"],
                int(fila["bloque"]),
                cedula,
                puesto,
                estado_hist,
                observacion
            ))

            conn.commit()
            st.session_state.msg_ok = True
            st.rerun()
