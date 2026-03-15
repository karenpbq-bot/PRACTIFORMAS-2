import streamlit as st
import pandas as pd
from base_datos import crear_proyecto, obtener_proyectos, eliminar_proyecto

def mostrar():
    st.title("📁 Gestión de Proyectos")
    
    # Usamos pestañas para que la pantalla no sea tan larga
    tab1, tab2 = st.tabs(["🆕 Registrar Proyecto", "📋 Listado y Búsqueda"])

    with tab1:
        st.subheader("Datos del Nuevo Proyecto (DNI)")
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                # 'codigo' es el DNI que pediste
                codigo = st.text_input("Código (DNI)", placeholder="Ej: PTF-001")
                nombre = st.text_input("Nombre del Proyecto", placeholder="Ej: Cocina Residencia")
            with col2:
                cliente = st.text_input("Cliente", placeholder="Nombre del cliente")
                partida = st.text_input("Partida", placeholder="Ej: Carpintería")

        # Botón pequeño (diseño compacto)
        if st.button("🚀 Registrar Proyecto"):
            if codigo and nombre:
                res = crear_proyecto(codigo, nombre, cliente, partida)
                if res:
                    st.success(f"✅ Proyecto {codigo} registrado.")
                    st.rerun()
            else:
                st.warning("⚠️ El Código (DNI) y el Nombre son obligatorios.")

    with tab2:
        st.subheader("Listado Maestro")
        # Buscador Universal que filtra por Código, Nombre o Cliente
        bus = st.text_input("🔍 Buscar...", placeholder="Escribe cualquier dato para filtrar")
        df_p = obtener_proyectos(bus)
        
        if not df_p.empty:
            st.dataframe(
                df_p[['codigo', 'proyecto_text', 'cliente', 'partida', 'estatus', 'avance']], 
                hide_index=True,
                use_container_width=True
            )
            
            # Opción para eliminar
            st.divider()
            with st.expander("🗑️ Zona de eliminación"):
                proy_sel = st.selectbox("Seleccione para eliminar", df_p['proyecto_display'].unique())
                id_eliminar = df_p[df_p['proyecto_display'] == proy_sel]['id'].values[0]
                if st.button("Borrar Permanentemente"):
                    eliminar_proyecto(id_eliminar)
                    st.success("Eliminado"); st.rerun()
        else:
            st.info("No se encontraron coincidencias.")
