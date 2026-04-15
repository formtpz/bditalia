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

    # =====================================================
    # PERFIL 4 → SELECCIÓN DE MODO
    # =====================================================
    if perfil == 4 or perfil == 5:

        if "modo_trabajo" not in st.session_state:
            st.session_state.modo_trabajo = "control_calidad"

        st.subheader("🔀 Seleccione modo de trabajo")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🧪 Control de Calidad"):
                st.session_state.modo_trabajo = "control_calidad"
                st.rerun()

        with col2:
            if st.button("👷 Operativo"):
                st.session_state.modo_trabajo = "operativo"
                st.rerun()

        st.info(f"Modo actual: {st.session_state.modo_trabajo.upper()}")

        perfil_efectivo = 4 if st.session_state.modo_trabajo == "control_calidad" else 3

    else:
        perfil_efectivo = perfil

    # =====================================================
    # MENSAJE GLOBAL
    # =====================================================
    if "msg_ok" not in st.session_state:
        st.session_state.msg_ok = None

    st.title("📍 Módulo de Asignaciones")

    if st.session_state.msg_ok:
        st.success(st.session_state.msg_ok)
        st.session_state.msg_ok = None

    # =====================================================
    # REGIONES
    # =====================================================
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
    # PERFIL 1
    # =====================================================
    if perfil_efectivo == 1:

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

            cur.execute("""
                INSERT INTO asignaciones_historial
                (asignacion_id, asignacion, bloque, region, usuario, puesto, proceso, estado)
                SELECT id, asignacion, bloque, region, %s, %s, 'operativo', 'asignado'
                FROM asignaciones
                WHERE asignacion = %s
                  AND region = %s
            """, (cedula, puesto, asignacion_sel, region_sel))

            conn.commit()
            st.session_state.msg_ok = "✅ Asignación manual realizada correctamente"
            st.rerun()

    # =====================================================
    # PERFIL OPERATIVO (3 o 4 en modo operativo)
    # =====================================================
    elif perfil_efectivo == 3:
        st.subheader("👷 Operativo - Panel de trabajo")
    
        # --- Autoasignación (sin cambios) ---
        if st.button("🧲 Autoasignarme una asignación completa"):
            cur.execute("""
                SELECT 1
                FROM asignaciones
                WHERE operador_actual = %s
                  AND estado_actual IN ('asignado', 'proceso', 'corregido')
                  AND proceso_actual = 'operativo'
                LIMIT 1
            """, (cedula,))
            if cur.fetchone():
                st.warning("⚠️ Ya tiene una asignación activa. Debe finalizar todos sus bloques antes de autoasignarse otra.")
            else:
                cur.execute("""
                    SELECT asignacion
                    FROM asignaciones
                    WHERE region = %s
                    GROUP BY asignacion
                    HAVING COUNT(*) = COUNT(
                        CASE WHEN estado_actual = 'pendiente'
                             AND proceso_actual = 'operativo'
                        THEN 1 END
                    )
                    ORDER BY asignacion
                    LIMIT 1
                """, (region_sel,))
                row = cur.fetchone()
                if not row:
                    st.info("No hay asignaciones elegibles para autoasignación en esta región")
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
                        WHERE asignacion = %s AND region = %s
                    """, (cedula, puesto, asignacion_sel, region_sel))
                    conn.commit()
                    st.session_state.msg_ok = "✅ Autoasignación realizada correctamente"
                    st.rerun()
    
        # --- Mostrar todas las asignaciones del operador (tabla resumen) ---
        df_asignaciones = pd.read_sql("""
            SELECT DISTINCT asignacion
            FROM asignaciones
            WHERE operador_actual = %s AND region = %s
            ORDER BY asignacion
        """, conn, params=(cedula, region_sel))
    
        if df_asignaciones.empty:
            st.info("No tienes ninguna asignación activa en esta región.")
            return
    
        # Selector de asignación para trabajo masivo
        asignacion_masiva = st.selectbox("📦 Seleccione la asignación para actualización masiva", df_asignaciones["asignacion"])
    
        # Obtener bloques de esa asignación
        df_bloques = pd.read_sql("""
            SELECT bloque, estado_actual, cantidad_rechazos, cantidad_aprobaciones
            FROM asignaciones
            WHERE operador_actual = %s AND region = %s AND asignacion = %s
            ORDER BY bloque
        """, conn, params=(cedula, region_sel, asignacion_masiva))
    
        if df_bloques.empty:
            st.warning("No hay bloques para esta asignación")
            return
    
        st.write("### Bloques actuales")
        st.dataframe(df_bloques[["bloque", "estado_actual"]], use_container_width=True)
    
        # --- Selección múltiple de bloques con el MISMO estado actual ---
        estados_disponibles = df_bloques["estado_actual"].unique()
        if len(estados_disponibles) == 0:
            st.info("No hay bloques para procesar")
            return
    
        # Permitir elegir un estado para filtrar los bloques a actualizar
        estado_filtro = st.selectbox("🔍 Filtrar bloques por estado actual", estados_disponibles)
    
        bloques_filtrados = df_bloques[df_bloques["estado_actual"] == estado_filtro]
        if bloques_filtrados.empty:
            st.info(f"No hay bloques con estado '{estado_filtro}'")
            return
    
        # Checkboxes para seleccionar varios bloques
        seleccion = {}
        st.write(f"**Bloques en estado '{estado_filtro}':**")
        for _, row in bloques_filtrados.iterrows():
            seleccion[row["bloque"]] = st.checkbox(f"Bloque {row['bloque']} - Estado actual: {row['estado_actual']}", key=f"masivo_{row['bloque']}")
    
        bloques_seleccionados = [bloque for bloque, selec in seleccion.items() if selec]
        if not bloques_seleccionados:
            st.info("Seleccione al menos un bloque para actualizar")
        else:
            # Determinar posibles nuevos estados según el estado común
            estado_comun = estado_filtro  # todos los seleccionados tienen este estado
            if estado_comun.startswith("rechazado"):
                opciones_estado = ["corregido"]
            elif estado_comun == "asignado":
                opciones_estado = ["proceso"]
            elif estado_comun == "proceso":
                opciones_estado = ["finalizado"]
            else:
                opciones_estado = []
    
            if not opciones_estado:
                st.info(f"El estado '{estado_comun}' no permite transiciones masivas")
            else:
                nuevo_estado_masivo = st.selectbox("🚀 Nuevo estado para los bloques seleccionados", opciones_estado)
                if st.button("💾 Aplicar cambio masivo"):
                    # Actualizar cada bloque seleccionado
                    for bloque in bloques_seleccionados:
                        if nuevo_estado_masivo == "corregido":
                            cur.execute("""
                                UPDATE asignaciones
                                SET estado_actual = 'corregido',
                                    proceso_actual = 'control_calidad'
                                WHERE asignacion = %s AND bloque = %s AND region = %s
                            """, (asignacion_masiva, int(bloque), region_sel))
                        else:
                            cur.execute("""
                                UPDATE asignaciones
                                SET estado_actual = %s
                                WHERE asignacion = %s AND bloque = %s AND region = %s
                            """, (nuevo_estado_masivo, asignacion_masiva, int(bloque), region_sel))
    
                        # Insertar en historial
                        cur.execute("""
                            INSERT INTO asignaciones_historial
                            (asignacion, bloque, region, usuario, puesto, proceso, estado)
                            VALUES (%s, %s, %s, %s, %s, 'operativo', %s)
                        """, (asignacion_masiva, int(bloque), region_sel, cedula, puesto, nuevo_estado_masivo))
    
                    conn.commit()
                    st.session_state.msg_ok = f"✅ {len(bloques_seleccionados)} bloque(s) actualizado(s) a '{nuevo_estado_masivo}'"
                    st.rerun()
    
        # --- Mantener también la opción individual (por si acaso) ---
        st.divider()
        st.write("### Modificación individual (opcional)")
        opciones_individuales = df_bloques[df_bloques["estado_actual"].isin(["asignado", "proceso", "rechazado", "corregido"])].copy()
        if not opciones_individuales.empty:
            opciones_individuales["label"] = opciones_individuales["asignacion"].astype(str) + " - Bloque " + opciones_individuales["bloque"].astype(str)
            seleccionado = st.selectbox("Seleccione un bloque para cambiar individualmente", opciones_individuales["label"])
            fila = opciones_individuales[opciones_individuales["label"] == seleccionado].iloc[0]
            estado_actual = fila["estado_actual"]
            if estado_actual.startswith("rechazado"):
                opciones_estado = ["corregido"]
            elif estado_actual == "asignado":
                opciones_estado = ["proceso"]
            elif estado_actual == "proceso":
                opciones_estado = ["finalizado"]
            else:
                opciones_estado = []
            if opciones_estado:
                nuevo_estado = st.selectbox("Nuevo estado (individual)", opciones_estado, key="individual")
                if st.button("💾 Guardar cambio individual"):
                    if nuevo_estado == "corregido":
                        cur.execute("""
                            UPDATE asignaciones
                            SET estado_actual = 'corregido',
                                proceso_actual = 'control_calidad'
                            WHERE asignacion = %s AND bloque = %s AND region = %s
                        """, (fila["asignacion"], int(fila["bloque"]), region_sel))
                    else:
                        cur.execute("""
                            UPDATE asignaciones
                            SET estado_actual = %s
                            WHERE asignacion = %s AND bloque = %s AND region = %s
                        """, (nuevo_estado, fila["asignacion"], int(fila["bloque"]), region_sel))
                    cur.execute("""
                        INSERT INTO asignaciones_historial
                        (asignacion, bloque, region, usuario, puesto, proceso, estado)
                        VALUES (%s, %s, %s, %s, %s, 'operativo', %s)
                    """, (fila["asignacion"], int(fila["bloque"]), region_sel, cedula, puesto, nuevo_estado))
                    conn.commit()
                    st.session_state.msg_ok = "✅ Estado actualizado correctamente"
                    st.rerun()
    # =====================================================
    # PERFIL CONTROL DE CALIDAD
    # =====================================================
    elif perfil_efectivo == 4:
    
        st.subheader("🧪 Control de Calidad")
    
        # 🔒 AUTOASIGNACIÓN CON VALIDACIÓN DE HISTORIAL--------------------------------------------------------------------------
        if st.button("🧲 Autoasignar para QC"):
    
            cur.execute("""
                SELECT a.asignacion
                FROM asignaciones a
                WHERE a.region = %s
                GROUP BY a.asignacion, a.region
                HAVING COUNT(*) = COUNT(
                    CASE WHEN a.estado_actual = 'finalizado' THEN 1 END
                )
                AND NOT EXISTS (
                    SELECT 1
                    FROM asignaciones_historial h
                    WHERE h.asignacion = a.asignacion
                      AND h.region = a.region
                      AND h.usuario = %s
                      AND h.proceso = 'operativo'
                      AND h.estado = 'asignado'
                )
                ORDER BY a.asignacion
                LIMIT 1
            """, (region_sel, cedula))
    
            row = cur.fetchone()
    
            if not row:
                st.warning("No hay asignaciones disponibles para QC (o usted fue operador).")
            else:
                asignacion_sel = row[0]
    
                #Almacenando en asignaciones la asignacion de QC y el estado pasa de finalizado a proceso
                cur.execute("""
                    UPDATE asignaciones
                    SET qc_actual = %s,
                        proceso_actual = 'control_calidad',
                        estado_actual = 'pendienteqc'
                    WHERE asignacion = %s
                        AND region = %s
                        AND estado_actual = 'finalizado'
                        AND qc_actual IS NULL
                """, (cedula, asignacion_sel, region_sel))

                #Almacenamiento en historial
                cur.execute("""
                INSERT INTO asignaciones_historial
                (asignacion_id, asignacion, bloque, region, usuario, puesto, proceso, estado)
                SELECT id, asignacion, bloque, region, %s, %s, 'control_calidad', 'asignado'
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
                st.session_state.msg_ok = "✅ Asignación tomada para Control de Calidad"
                st.rerun()

        df = pd.read_sql("""
            SELECT asignacion, bloque, estado_actual,
                   cantidad_rechazos, cantidad_aprobaciones
            FROM asignaciones
            WHERE qc_actual = %s
              AND region = %s
            ORDER BY asignacion, bloque
        """, conn, params=(cedula, region_sel))

        st.dataframe(df, use_container_width=True)

        opciones = df[df["estado_actual"].isin(["pendienteqc", "corregido"])].copy()

        if opciones.empty:
            return

        opciones["label"] = opciones["asignacion"] + " - Bloque " + opciones["bloque"].astype(str)
        seleccionado = st.selectbox("Seleccione bloque a revisar", opciones["label"])
        fila = opciones[opciones["label"] == seleccionado].iloc[0]

        nuevo_estado = st.selectbox("Resultado QC", ["aprobado", "rechazado"])
        observacion = st.text_area("Observación (solo si rechaza)")

        if st.button("💾 Guardar revisión"):

            if nuevo_estado == "aprobado":
                cur.execute("""
                    UPDATE asignaciones
                    SET cantidad_aprobaciones = cantidad_aprobaciones + 1,
                        estado_actual = 'aprobado'
                    WHERE asignacion = %s
                      AND bloque = %s
                      AND region = %s
                """, (fila["asignacion"], int(fila["bloque"]), region_sel))
                estado_hist = "aprobado"

            else:
                cur.execute("""
                    UPDATE asignaciones
                    SET cantidad_rechazos = cantidad_rechazos + 1,
                        estado_actual = 'rechazado ' || (cantidad_rechazos + 1),
                        proceso_actual = 'operativo'
                    WHERE asignacion = %s
                      AND bloque = %s
                      AND region = %s
                """, (fila["asignacion"], int(fila["bloque"]), region_sel))

                cur.execute("""
                    SELECT estado_actual
                    FROM asignaciones
                    WHERE asignacion = %s
                      AND bloque = %s
                      AND region = %s
                """, (fila["asignacion"], int(fila["bloque"]), region_sel))

                estado_hist = cur.fetchone()[0]

            cur.execute("""
                INSERT INTO asignaciones_historial
                (asignacion_id, asignacion, bloque, region, usuario, puesto, proceso, estado, observacion)
                SELECT id, asignacion, bloque, region, %s, %s, 'control_calidad', %s, %s
                FROM asignaciones
                WHERE asignacion = %s
                    AND bloque = %s
                    AND region = %s
            """, (
                cedula,
                puesto,
                estado_hist,
                observacion,
                fila["asignacion"],
                int(fila["bloque"]),
                region_sel
            ))

            conn.commit()
            st.session_state.msg_ok = "✅ Revisión guardada correctamente"
            st.rerun()

    else:
        st.error("⛔ Perfil no autorizado para este módulo")
