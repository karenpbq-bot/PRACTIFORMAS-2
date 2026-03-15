import streamlit as st
import pandas as pd
from datetime import timedelta, datetime, date
from base_datos import *
import seguimiento, ejecucion, login, usuarios, incidencias 
import plotly.express as px

# =========================================================
# CONFIGURACIÓN INICIAL Y SESIÓN
# =========================================================
st.set_page_config(layout="wide", page_title="Carpintería Pro V2")
inicializar_bd()

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if 'id_p_sel' not in st.session_state:
    st.session_state.id_p_sel = None 

if not st.session_state.autenticado:
    login.login_screen()
    st.stop()

rol_usuario = st.session_state.rol
id_usuario = st.session_state.id_usuario
ETAPAS = ["Diseño", "Fabricación", "Traslado", "Instalación", "Entrega"]

# =========================================================
# BARRA LATERAL (SIDEBAR)
# =========================================================
with st.sidebar:
    st.title("🪚 PRACTIFORMAS")
    st.write(f"Usuario: **{st.session_state.nombre_real}**")
    st.caption(f"Rol: {rol_usuario}")
    
    if st.button("🔄 Ver Todos los Proyectos"):
        st.session_state.id_p_sel = None
        st.rerun()
    
    # Reemplaza el bloque viejo por este:
    opciones = ["Proyectos", "Seguimiento", "Incidencias", "Gantt", "Usuarios"]
    menu = st.sidebar.radio("MENÚ PRINCIPAL", opciones)
    
    menu = st.sidebar.radio("MENÚ PRINCIPAL", opciones)
    
    st.write("---")
    if st.button("🚪 Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

# =========================================================
# MÓDULO: PANEL DE GESTIÓN DETALLADA
# =========================================================
    else:
        id_p = st.session_state.id_p_sel
        supabase = conectar()
        res_aux = supabase.table("proyectos").select("*").eq("id", id_p).execute()
        
        if not res_aux.data:
            st.error("⚠️ El proyecto seleccionado ya no existe.")
            st.session_state.id_p_sel = None
            if st.button("🔄 Volver"): st.rerun()
            st.stop()
        
        p_data = res_aux.data[0]
        if st.sidebar.button("⬅️ VOLVER A LA CARTERA"):
            st.session_state.id_p_sel = None
            st.rerun()

        st.title(f"🚀 {p_data['proyecto_text']} — {p_data['cliente']}")
        t1, t2, t3 = st.tabs(["📋 Productos e Inventario", "📅 Cronograma Contractual", "🚨 Zona de Peligro"])
        
        with t1:
            st.subheader("📦 Gestión de Inventario")
            col_izq, col_der = st.columns(2)
            with col_izq:
                with st.expander("➕ Creación Manual"):
                    with st.form("nuevo_manual", clear_on_submit=True):
                        u_m = st.text_input("Ubicación")
                        t_m = st.text_input("Tipo")
                        c_cant = st.number_input("Cantidad", min_value=1, step=1)
                        c_ml = st.number_input("Metros Lineales (ML)", min_value=0.0, format="%.2f")
                        if st.form_submit_button("Añadir Producto"):
                            agregar_producto_manual(id_p, u_m, t_m, c_cant, c_ml)
                            st.rerun()
            with col_der:
                with st.expander("📥 Importación"):
                    f_up = st.file_uploader("Documento Archicad (.xlsx)", type=["xlsx"])
                    if f_up and st.button("🚀 Procesar Documento"):
                        df_ex = pd.read_excel(f_up)
                        if df_ex.iloc[0].isnull().all(): df_ex = pd.read_excel(f_up, skiprows=1)
                        for _, r in df_ex.iterrows():
                            agregar_producto_manual(id_p, r['UBICACION'], r['TIPO'], r['CTD'], r['Medidas (ml)'])
                        st.success("Productos importados"); st.rerun()

            st.divider()
            # Lista de productos con edición
            prods_res = supabase.table("productos").select("*").eq("proyecto_id", id_p).execute()
            if prods_res.data:
                for r in prods_res.data:
                    with st.container(border=True):
                        cols = st.columns([2, 2, 1, 1, 0.5, 0.5])
                        nu = cols[0].text_input("U", r['ubicacion'], key=f"u_{r['id']}", label_visibility="collapsed")
                        nt = cols[1].text_input("T", r['tipo'], key=f"t_{r['id']}", label_visibility="collapsed")
                        nc = cols[2].number_input("C", value=int(r['ctd']), key=f"c_{r['id']}", label_visibility="collapsed")
                        nm = cols[3].number_input("M", value=float(r['ml']), key=f"m_{r['id']}", label_visibility="collapsed")
                        if cols[4].button("💾", key=f"s_{r['id']}"):
                            actualizar_producto(r['id'], nu, nt, nc, nm)
                            st.toast("Guardado")
                        if cols[5].button("🗑️", key=f"d_{r['id']}"):
                            eliminar_producto(r['id'])
                            st.rerun()

            # Exportación
            st.divider()
            df_reporte = obtener_datos_reporte(id_p)
            if not df_reporte.empty:
                col_ex1, col_ex2 = st.columns(2)
                import io
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_reporte.to_excel(writer, index=False, sheet_name='Inventario')
                col_ex1.download_button("📥 Descargar Excel", buffer.getvalue(), f"Inventario_{p_data['proyecto_text']}.xlsx", use_container_width=True)
                
                msg = f"📋 *REPORTE PRACTIFORMAS*%0A*Proyecto:* {p_data['proyecto_text']}%0A*Total Unidades:* {int(df_reporte['Cantidad'].sum())}%0A_Generado desde la App_"
                st.link_button("🟢 Enviar WhatsApp", f"https://wa.me/?text={msg}", use_container_width=True)

        with t2:
            st.subheader("📅 Gantt Planificado")
            # Mapeo dinámico para el Gantt Planificado de la Nube
            etapas_conf = [
                ("Diseño", "p_dis_i", "p_dis_f"), ("Fabricación", "p_fab_i", "p_fab_f"),
                ("Traslado", "p_tra_i", "p_tra_f"), ("Instalación", "p_ins_i", "p_ins_f"),
                ("Entrega", "p_ent_i", "p_ent_f")
            ]
            data_gantt_plan = [dict(Etapa=e, Inicio=p_data[i], Fin=p_data[f], Color="#D5DBDB") for e, i, f in etapas_conf]
            fig = px.timeline(pd.DataFrame(data_gantt_plan), x_start="Inicio", x_end="Fin", y="Etapa", color="Color", color_discrete_map="identity")
            fig.update_yaxes(categoryorder="array", categoryarray=["Entrega", "Instalación", "Traslado", "Fabricación", "Diseño"])
            st.plotly_chart(fig, use_container_width=True)

        with t3:
            if rol_usuario == "Administrador":
                if st.button("🚨 ELIMINAR PROYECTO COMPLETO", type="primary"):
                    eliminar_proyecto(id_p)
                    st.session_state.id_p_sel = None
                    st.rerun()

# =========================================================
# OTROS MÓDULOS (LLAMADAS EXTERNAS)
# =========================================================
if menu == "Proyectos":
    proyectos.mostrar() # <--- Esta es la llamada al nuevo archivo
elif menu == "Seguimiento": 
    seguimiento.mostrar(supervisor_id=id_usuario if rol_usuario == "Supervisor" else None)
elif menu == "Gantt": 
    ejecucion.mostrar()
elif menu == "Usuarios":
    usuarios.mostrar()
elif menu == "Incidencias":
    incidencias.mostrar()

