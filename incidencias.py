import streamlit as st
import pandas as pd
import io
from datetime import datetime
from base_datos import conectar, obtener_proyectos, registrar_incidencia_detallada, obtener_incidencias_resumen

def mostrar():
    st.header("⚠️ Gestión de Requerimientos")
    
    # 1. MEMORIA TEMPORAL (CARRITOS SEPARADOS)
    if 'tmp_piezas' not in st.session_state: st.session_state.tmp_piezas = []
    if 'tmp_mats' not in st.session_state: st.session_state.tmp_mats = []

    # 2. PESTAÑAS
    tab_p, tab_m, tab_h = st.tabs(["🧩 Requerimiento de Piezas", "📦 Requerimiento de Material", "📜 Historial de Requerimientos"])

    # Carga de datos maestros
    df_p = obtener_proyectos("")
    dict_proyectos = {row['proyecto_text']: row['id'] for _, row in df_p.iterrows()}
    MOTIVOS = ["Faltante", "Cambio", "Pieza Dañada", "Otros"]

    # =========================================================
    # --- PESTAÑA 1: PIEZAS (CENTRO DE CORTE) ---
    # =========================================================
    with tab_p:
        st.subheader("Configuración del Bloque de Piezas")
        col1, col2 = st.columns(2)
        proy_p = col1.selectbox("Proyecto:", list(dict_proyectos.keys()), key="proy_p")
        motivo_p = col2.selectbox("Motivo del Requerimiento:", MOTIVOS, key="mot_p")
        
        with st.expander("➕ Agregar Pieza a la Matriz", expanded=True):
            # Fila 1: Identificación
            c1, c2, c3 = st.columns([2,1,1])
            desc = c1.text_input("Descripción de la pieza", key="p_desc_in")
            cant = c2.number_input("Cantidad", min_value=1, key="p_cant_in")
            ubi = c3.text_input("Ubicación (Módulo)", placeholder="Ej: B101", key="p_ubi_in")
            
            # Fila 2: Dimensiones Reales y Rotación (REQUERIMIENTO AJUSTADO)
            c4, c5, c6, c7 = st.columns(4)
            veta = c4.number_input("Veta (Largo mm)", min_value=0, value=0, key="p_veta_in")
            nveta = c5.number_input("No Veta (Ancho mm)", min_value=0, value=0, key="p_nveta_in")
            material = c6.text_input("Material / Color", key="p_mat_in")
            rot = c7.selectbox("Rotación", [0, 1], help="0: Sin rotación, 1: Con rotación", key="p_rot_in")
            
            # Fila 3: Tapacantos
            st.write("**Tapacantos (mm)**")
            t1, t2, t3, t4 = st.columns(4)
            tf = t1.text_input("Frontal (F)", key="p_tf")
            tp = t2.text_input("Posterior (P)", key="p_tp")
            td = t3.text_input("Derecho (D)", key="p_td")
            ti = t4.text_input("Izquierdo (I)", key="p_ti")
            
            obs = st.text_area("Observaciones específicas de la pieza", key="p_obs_in")
            
            if st.button("➕ Añadir a Matriz de Envío", key="btn_add_p"):
                st.session_state.tmp_piezas.append({
                    "descripcion": desc, "veta": veta, "no_veta": nveta, "cantidad": cant,
                    "ubicacion": ubi, "material": material, "tc_frontal": tf, "tc_posterior": tp,
                    "tc_derecho": td, "tc_izquierdo": ti, "rotacion": rot, "observaciones": obs
                })
                st.rerun()

        # Mostrar Tabla de Piezas acumuladas
        if st.session_state.tmp_piezas:
            st.write("### 📋 Bloque de Piezas a Enviar")
            st.dataframe(pd.DataFrame(st.session_state.tmp_piezas), use_container_width=True)
            if st.button("🚀 ENVIAR REQUERIMIENTO CONSOLIDADO (PIEZAS)", type="primary"):
                registrar_incidencia_detallada(dict_proyectos[proy_p], "Piezas", motivo_p, st.session_state.tmp_piezas, [], st.session_state.get('id_usuario'))
                st.session_state.tmp_piezas = []
                st.success("Requerimiento enviado a Centro de Corte."); st.rerun()

    # =========================================================
    # --- PESTAÑA 2: MATERIALES (ALMACÉN) ---
    # =========================================================
    with tab_m:
        st.subheader("Configuración del Bloque de Materiales")
        col1m, col2m = st.columns(2)
        proy_m = col1m.selectbox("Proyecto:", list(dict_proyectos.keys()), key="proy_m")
        motivo_m = col2m.selectbox("Motivo del Requerimiento:", MOTIVOS, key="mot_m")
        
        with st.container(border=True):
            cm1, cm2, cm3 = st.columns([2,1,1])
            m_desc = cm1.text_input("Descripción (Accesorio, Pintura, etc.)", key="m_desc_in")
            m_cant = cm2.number_input("Cant.", min_value=1, key="m_cant_in")
            m_unidad = cm3.selectbox("Unidad", ["Und", "Mts", "Lts", "Par", "Kit"], key="m_uni_in")
            m_obs = st.text_input("Observaciones de material", key="m_obs_in")
            
            if st.button("➕ Añadir Material a la Lista", key="btn_add_m"):
                st.session_state.tmp_mats.append({
                    "descripcion": m_desc, "cantidad": m_cant, "unidad": m_unidad, "observaciones": m_obs
                })
                st.rerun()

        if st.session_state.tmp_mats:
            st.write("### 📋 Bloque de Materiales a Enviar")
            st.table(pd.DataFrame(st.session_state.tmp_mats))
            if st.button("🚀 ENVIAR REQUERIMIENTO CONSOLIDADO (MATERIALES)", type="primary"):
                registrar_incidencia_detallada(dict_proyectos[proy_m], "Materiales", motivo_m, [], st.session_state.tmp_mats, st.session_state.get('id_usuario'))
                st.session_state.tmp_mats = []
                st.success("Requerimiento enviado a Almacén."); st.rerun()

    # =========================================================
    # --- PESTAÑA 3: HISTORIAL DE REQUERIMIENTOS ---
    # =========================================================
    with tab_h:
        historial = obtener_incidencias_resumen()
        if not historial.empty:
            for _, inc in historial.iterrows():
                with st.expander(f"REQ-{inc['id']} | {inc['proyecto_text']} | {inc['tipo_requerimiento']} - {inc['estado']}"):
                    st.write(f"**Motivo:** {inc['categoria']} | **Fecha:** {inc['created_at']}")
                    if inc.get('detalles'):
                        st.dataframe(pd.DataFrame(inc['detalles']), use_container_width=True)
                    
                    # Espacio para botón de exportación futuro
                    st.button("📥 Exportar Excel", key=f"exp_{inc['id']}")
        else:
            st.info("No hay requerimientos registrados.")
