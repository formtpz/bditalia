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
        st.warning("⚠️ No existen regiones registradas en el sistema")
        return

    region_sel = st.selectbox("🌍 Seleccione región", regiones)

    # =====================================================
    # ======================= OPERADOR ====================
    # =====================================================
    if perfil == 3:
        st.subheader("👷 Operativo")

        # ---------- AUTOASIGNACIÓN ----------
        if st.button("🧲 Autoasignarme una asignación completa"):

            # 🔒 VALIDAR SI YA TIENE ASIGNACIÓN ACTIVA
            cur.execute("""
                SELECT 1
                FROM asignaciones
                WHERE operador_actual = %s
                  AND estado_actual NOT LIKE 'rechazado%%'
                  AND estado_actual <> 'finalizado'
                LIMIT 1
            """, (cedula,))

            tiene_asignacion_activa = cur.fetchone()

            if tiene_asignacion_activa:
                st.warning("⚠️ Ya tiene una asignación activa. Debe finalizarla antes de autoasignarse otra.")
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
                    st.info("No hay asignaciones pendientes en esta región")
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

                    cur.execute("""
                        INSERT INTO asignaciones_historial
                        (asignacion_id, asignacion, bloque, region, usuario, puesto, proceso, estado)
                        SELECT id, asignacion, bloque, region, %s, %s, 'operativo', 'asignado'
                        FROM asignaciones
                        WHERE asignacion = %s
                          AND region = %s
                    """, (cedula, puesto, asignacion_sel, region_sel))

                    conn.commit()
                    st.session_state.msg_ok = True
                    st.rerun()

        # ---------- TABLA SOLO LECTURA ----------
        filtro = st.selectbox(
            "Filtrar por estado",
            ["Todos", "rechazado", "corregido", "asignado", "proceso", "finalizado"]
        )

        where = ""
        params = [cedula, region_sel]

        if filtro != "Todos":
            where = " AND estado_actual LIKE %s"
            params.append(f"%{filtro}%")

        df = pd.read_sql(f"""
            SELECT asignacion, bloque, estado_actual,
                   cantidad_rechazos, cantidad_aprobaciones
            FROM asignaciones
            WHERE operador_actual = %s
              AND region = %s
            {where}
            ORDER BY asignacion, bloque
        """, conn, params=params)

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
            if nuevo_estado == "corregido":
                cur.execute("""
                    UPDATE asignaciones
                    SET estado_actual = 'corregido',
                        proceso_actual = 'control_calidad'
                    WHERE asignacion = %s
                      AND bloque = %s
                      AND region = %s
                """, (fila["asignacion"], int(fila["bloque"]), region_sel))
            else:
                cur.execute("""
                    UPDATE asignaciones
                    SET estado_actual = %s
                    WHERE asignacion = %s
                      AND bloque = %s
                      AND region = %s
                """, (nuevo_estado, fila["asignacion"], int(fila["bloque"]), region_sel))

            cur.execute("""
                INSERT INTO asignaciones_historial
                (asignacion, bloque, region, usuario, puesto, proceso, estado)
                VALUES (%s,%s,%s,%s,%s,'operativo',%s)
            """, (
                fila["asignacion"],
                int(fila["bloque"]),
                region_sel,
                cedula,
                puesto,
                nuevo_estado
            ))

            conn.commit()
            st.session_state.msg_ok = True
            st.rerun()

    # =====================================================
    # PERFIL NO VÁLIDO
    # =====================================================
    else:
        st.error("⛔ Perfil no autorizado para este módulo")

