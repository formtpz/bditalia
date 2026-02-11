import streamlit as st
import pandas as pd
from db import get_connection
from permisos import validar_acceso


def render():
    validar_acceso("Asignación de Producción")

    usuario = st.session_state["usuario"]
    cedula = usuario["cedula"]
    perfil = usuario["perfil"]
    puesto = usuario["puesto"]

    conn = get_connection()
    cur = conn.cursor()

    # =========================
    # Mensaje persistente
    # =========================
    if "msg_ok" not in st.session_state:
        st.session_state.msg_ok = False

    st.title("📍 Módulo de Asignaciones")

    if st.session_state.msg_ok:
        st.success("✅ Cambio guardado correctamente")
        st.session_state.msg_ok = False

    # =========================
    # Cargar regiones disponibles
    # =========================
    cur.execute("""
        SELECT DISTINCT region
        FROM asignaciones
        WHERE region IS NOT NULL
        ORDER BY region
    """)
    regiones = [r[0] for r in cur.fetchall()]

    if not regiones:
        st.warning("⚠️ No existen regiones registradas")
        return

    region_sel = st.selectbox("🌍 Seleccione región", regiones)

    # =====================================================
    # ======================= PERFIL 1 ====================
    # =====================================================
    if perfil == 1:
        st.subheader("👑 Asignación Manual por Región")

        df_operadores = pd.read_sql("""
            SELECT cedula, nombre_completo
            FROM personal
            WHERE estado = 'activo'
              AND perfil = 3
            ORDER BY nombre_completo
        """, conn)

        if df_operadores.empty:
            st.warning("No existen operadores activos")
            return

        operador_sel = st.selectbox(
            "👷 Seleccione operador",
            df_operadores["nombre_completo"]
        )

        cedula_operador = df_operadores[
            df_operadores["nombre_completo"] == operador_sel
        ]["cedula"].iloc[0]

        df_asignaciones = pd.read_sql("""
            SELECT asignacion
            FROM asignaciones
            WHERE region = %s
            GROUP BY asignacion
            HAVING COUNT(*) = COUNT(
                CASE WHEN estado_actual = 'pendiente' THEN 1 END
            )
            ORDER BY asignacion
        """, conn, params=[region_sel])

        if df_asignaciones.empty:
            st.info("No hay asignaciones completamente pendientes en esta región")
            return

        asignacion_sel = st.selectbox(
            "📦 Seleccione asignación pendiente",
            df_asignaciones["asignacion"]
        )

        if st.button("📌 Asignar manualmente"):
            cur.execute("""
                UPDATE asignaciones
                SET operador_actual = %s,
                    proceso_actual = 'operativo',
                    estado_actual = 'asignado'
                WHERE asignacion = %s
                  AND region = %s
                  AND estado_actual = 'pendiente'
            """, (cedula_operador, asignacion_sel, region_sel))

            # HISTORIAL
            cur.execute("""
                INSERT INTO asignaciones_historial
                (asignacion_id, asignacion, bloque, region, usuario, puesto, proceso, estado)
                SELECT id, asignacion, bloque, region, %s, %s, 'operativo', 'asignado'
                FROM asignaciones
                WHERE asignacion = %s
                  AND region = %s
            """, (
                cedula,
                puesto,
                asignacion_sel,
                region_sel
            ))

            conn.commit()
            st.success("✅ Asignación realizada correctamente")
            st.rerun()

    # =====================================================
    # ======================= OPERADOR ====================
    # =====================================================
    elif perfil == 3:
        st.subheader("👷 Operativo")

        if st.button("🧲 Autoasignarme una asignación completa"):

            cur.execute("""
                SELECT 1
                FROM asignaciones
                WHERE operador_actual = %s
                  AND estado_actual IN ('asignado', 'proceso', 'corregido')
                LIMIT 1
            """, (cedula,))

            if cur.fetchone():
                st.warning("⚠️ Ya tiene una asignación en proceso.")
            else:
                cur.execute("""
                    SELECT asignacion
                    FROM asignaciones
                    WHERE estado_actual = 'pendiente'
                      AND region = %s
                    GROUP BY asignacion
                    ORDER BY asignacion
                    LIMIT 1
                """, (region_sel,))
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
                          AND region = %s
                          AND estado_actual = 'pendiente'
                    """, (cedula, asignacion_sel, region_sel))

                    # HISTORIAL RESTAURADO
                    cur.execute("""
                        INSERT INTO asignaciones_historial
                        (asignacion_id, asignacion, bloque, region, usuario, puesto, proceso, estado)
                        SELECT id, asignacion, bloque, region, %s, %s, 'operativo', 'asignado'
                        FROM asignaciones
                        WHERE asignacion = %s
                          AND region = %s
                    """, (
                        cedula,
                        puesto,
                        asignacion_sel,
                        region_sel
                    ))

                    conn.commit()
                    st.session_state.msg_ok = True
                    st.rerun()

        df = pd.read_sql("""
            SELECT asignacion, bloque, estado_actual,
                   cantidad_rechazos, cantidad_aprobaciones
            FROM asignaciones
            WHERE operador_actual = %s
              AND region = %s
            ORDER BY asignacion, bloque
        """, conn, params=(cedula, region_sel))

        st.dataframe(df, use_container_width=True)

    # =====================================================
    # ================= CONTROL DE CALIDAD ================
    # =====================================================
    elif perfil == 4:
        st.subheader("🧪 Control de Calidad")

        if st.button("🧲 Autoasignar para QC"):
            cur.execute("""
                SELECT asignacion
                FROM asignaciones
                WHERE region = %s
                GROUP BY asignacion
                HAVING COUNT(*) = COUNT(
                    CASE WHEN estado_actual = 'finalizado' THEN 1 END
                )
                ORDER BY asignacion
                LIMIT 1
            """, (region_sel,))
            row = cur.fetchone()

            if not row:
                st.info("No hay asignaciones listas para QC")
            else:
                asignacion_sel = row[0]

                cur.execute("""
                    UPDATE asignaciones
                    SET qc_actual = %s,
                        proceso_actual = 'control_calidad'
                    WHERE asignacion = %s
                      AND region = %s
                """, (cedula, asignacion_sel, region_sel))

                # HISTORIAL RESTAURADO PARA QC
                cur.execute("""
                    INSERT INTO asignaciones_historial
                    (asignacion_id, asignacion, bloque, region, usuario, puesto, proceso, estado)
                    SELECT id, asignacion, bloque, region, %s, %s, 'control_calidad', estado_actual
                    FROM asignaciones
                    WHERE asignacion = %s
                      AND region = %s
                """, (
                    cedula,
                    puesto,
                    asignacion_sel,
                    region_sel
                ))

                conn.commit()
                st.session_state.msg_ok = True
                st.rerun()

        df = pd.read_sql("""
            SELECT asignacion, bloque, estado_actual
            FROM asignaciones
            WHERE qc_actual = %s
              AND region = %s
            ORDER BY asignacion, bloque
        """, conn, params=(cedula, region_sel))

        st.dataframe(df, use_container_width=True)

    # =====================================================
    # ================= PERFIL NO VÁLIDO ==================
    # =====================================================
    else:
        st.error("⛔ Perfil no autorizado para este módulo")

