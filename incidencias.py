import streamlit as st
import pandas as pd
import io
from datetime import date
from base_datos import conectar, obtener_proyectos, registrar_incidencia_detallada, obtener_incidencias_resumen

def mostrar():
    st.header("⚠️ Gestión de Requerimientos")
    
    # 3 Pestañas solicitadas
    tab_p, tab_m, tab_h = st.tabs(["🧩 Requerimiento de Piezas", "📦 Requerimiento de Material", "📜 Historial de Reportes"])

    df_p = obtener_proyectos("")
    dict_proyectos = {row['proyecto_text']: row['id'] for _, row in df_p.iterrows()}
    MOTIVOS = ["Faltante", "Cambio", "Otros"]

    # --- PESTAÑA 1: PIEZAS ---
    with tab_p:
        st.subheader("Configuración del Pedido de Piezas")
        col1, col2 = st.columns(2)
        proy_p = col1.selectbox("Proyecto:", list(dict_proyectos.keys()), key="proy_p")
        motivo_p = col2.selectbox("Motivo del Requerimiento:", MOTIVOS, key="mot_p")
        
        if 'tmp_piezas' not in st.session_state: st.session_state.tmp_piezas = []

        with st.expander("➕ Agregar Pieza a la Matriz", expanded=True):
            c1, c2, c3 = st.columns([2,1,1])
            desc = c1.text_input("Descripción de la pieza")
            cant = c2.number_input("Cantidad", min_value=1, key="p_cant")
            ubi = c3.text_input("Ubicación", placeholder="Ej: B101")
            
            # --- AJUSTE TÉCNICO: DIMENSIONES Y ROTACIÓN BINARIA ---
            c4, c5, c6, c7 = st.columns(4)
            veta = c4.number_input("Veta (mm)", min_value=0, value=0)
            nveta = c5.number_input("No Veta (mm)", min_value=0, value=0)
            material = c6.text_input("Material / Color")
            rot = c7.selectbox("Rotación", [0, 1], help="0: Sin rotación, 1: Rotada")
            
            st.write("**Tapacantos**")
            t1, t2, t3, t4 = st.columns(4)
            tf, tp, td, ti = t1.text_input("Frontal (F)"), t2.text_input("Posterior (P)"), t3.text_input("Derecho (D)"), t4.text_input("Izquierdo (I)")
            
            obs = st.text_area("Observaciones específicas")
            
            if st.button("➕ Añadir a la lista temporal"):
                st.session_state.tmp_piezas.append({
                    "descripcion": desc, "veta": veta, "no_veta": nveta, "cantidad": cant,
                    "ubicacion": ubi, "material": material, "tc_frontal": tf, "tc_posterior": tp,
                    "tc_derecho": td, "tc_izquierdo": ti, "rotacion": rot, "observaciones": obs
                })
                st.rerun() # Actualiza la matriz en pantalla inmediatamente

        if st.session_state.tmp_piezas:
            st.write("### 📋 Matriz Consolidada de Piezas")
            st.dataframe(pd.DataFrame(st.session_state.tmp_piezas), use_container_width=True)
            if st.button("🚀 ENVIAR REQUERIMIENTO CONSOLIDADO (PIEZAS)", type="primary"):
                registrar_incidencia_detallada(dict_proyectos[proy_p], "Piezas", motivo_p, st.session_state.tmp_piezas, [], st.session_state.id_usuario)
                st.session_state.tmp_piezas = []
                st.success("Bloque de piezas enviado con éxito"); st.rerun())

    # --- PESTAÑA 2: MATERIALES ---
    with tab_m:
        st.subheader("Configuración del Pedido de Materiales")
        col1m, col2m = st.columns(2)
        proy_m = col1m.selectbox("Proyecto:", list(dict_proyectos.keys()), key="proy_m")
        motivo_m = col2m.selectbox("Motivo del Requerimiento:", MOTIVOS, key="mot_m")
        
        if 'tmp_mats' not in st.session_state: st.session_state.tmp_mats = []

        with st.container(border=True):
            cm1, cm2, cm3 = st.columns([2,1,1])
            m_desc = cm1.text_input("Descripción (Accesorio, Pintura, etc)")
            m_cant = cm2.number_input("Cant.", min_value=1, key="m_cant_input")
            m_unidad = cm3.selectbox("Unidad", ["Und", "Mts", "Lts", "Par"])
            m_obs = st.text_input("Observaciones de material")
            
            if st.button("➕ Añadir Material a la lista"):
                st.session_state.tmp_mats.append({
                    "descripcion": m_desc, "cantidad": m_cant, "unidad": m_unidad, "observaciones": m_obs
                })
                st.rerun()

        if st.session_state.tmp_mats:
            st.write("### 📋 Matriz Consolidada de Materiales")
            st.table(pd.DataFrame(st.session_state.tmp_mats))
            if st.button("🚀 ENVIAR REQUERIMIENTO CONSOLIDADO (MATERIALES)", type="primary"):
                registrar_incidencia_detallada(dict_proyectos[proy_m], "Materiales", motivo_m, [], st.session_state.tmp_mats, st.session_state.id_usuario)
                st.session_state.tmp_mats = []
                st.success("Bloque de materiales enviado con éxito"); st.rerun()

    # --- PESTAÑA 3: HISTORIAL ---
    with tab_h:
        st.subheader("📜 Historial de Requerimientos Consolidados")
        historial = obtener_incidencias_resumen()
        if not historial.empty:
            for _, inc in historial.iterrows():
                # El expander ahora representa el REQUERIMIENTO completo
                with st.expander(f"📦 REQ-{inc['id']} | {inc['proyecto_text']} | {inc['tipo_requerimiento']}"):
                    st.write(f"**Motivo:** {inc['categoria']} | **Estado:** {inc['estado']}")
                    
                    # Verificamos si hay detalles (JSON) para mostrar la tabla interna
                    if 'detalles' in inc and inc['detalles']:
                        st.write("**Detalle del Requerimiento:**")
                        st.dataframe(pd.DataFrame(inc['detalles']), use_container_width=True)
                    
                    # Botón para descargar el Excel consolidado de este REQ específico
                    # ... (lógica de exportación)
