import streamlit as st
import pandas as pd
from datetime import datetime
import io
from base_datos import conectar, obtener_proyectos, obtener_productos_por_proyecto, obtener_seguimiento, guardar_seguimiento

# =========================================================
# 1. CONFIGURACIÓN Y DICCIONARIOS MAESTROS (RESPETADOS)
# =========================================================
MAPEO_HITOS = {
    "Diseñado": "🗺️", "Fabricado": "🪚", "Material en Obra": "🚛",
    "Material en Ubicación": "📍", "Instalación de Estructura": "📦", 
    "Instalación de Puertas o Frentes": "🗄️", "Revisión y Observaciones": "🔍", "Entrega": "🤝"
}

HITOS_LIST = list(MAPEO_HITOS.keys())

def obtener_fecha_formateada():
    return datetime.now().strftime("%d/%m/%Y")

# =========================================================
# 2. LÓGICA DE CASCADA Y SEGURIDAD (V2)
# =========================================================
def registrar_hitos_cascada(p_id, hito_final, fecha_str):
    supabase = conectar()
    try:
        safe_p_id = int(p_id)
        idx_limite = HITOS_LIST.index(hito_final)
        hitos_a_marcar = HITOS_LIST[:idx_limite + 1]
        
        # Consultamos fechas existentes para NO sobreescribir historial
        existentes = supabase.table("seguimiento").select("hito").eq("producto_id", safe_p_id).execute()
        hitos_con_data = [r['hito'] for r in existentes.data] if existentes.data else []

        for h in hitos_a_marcar:
            if h not in hitos_con_data:
                supabase.table("seguimiento").upsert({
                    "producto_id": safe_p_id, "hito": str(h), "fecha": str(fecha_str)
                }, on_conflict="producto_id, hito").execute()
    except Exception as e:
        st.error(f"Error en cascada: {e}")

# =========================================================
# 3. INTERFAZ PRINCIPAL
# =========================================================
def mostrar(supervisor_id=None):
    # CSS para Sticky Header y Scroll Independiente
    st.markdown("""
        <style>
        .sticky-top { position: sticky; top: 0; background: white; z-index: 999; padding: 10px 0; border-bottom: 3px solid #FF8C00; }
        .scroll-area { max-height: 600px; overflow-y: auto; overflow-x: hidden; border: 1px solid #eee; padding: 15px; border-radius: 8px; }
        .metric-box { background-color: #f8f9fa; padding: 10px; border-radius: 8px; text-align: center; border: 1px solid #dee2e6; }
        </style>
    """, unsafe_allow_html=True)
    
    st.header("📈 Seguimiento de Producción V2")
    supabase = conectar()

    # --- 5. ACCIONES GLOBALES (BARRA SUPERIOR) ---
    col_g1, col_g2, col_g3 = st.columns([1, 1, 2])
    fecha_reg = col_g1.date_input("📅 Fecha Registro:", datetime.now())

    # --- 1. BLOQUE 1: BÚSQUEDA DE PROYECTO (PLEGABLE) ---
    with st.expander("📁 BLOQUE 1: BÚSQUEDA DE PROYECTO", expanded=not st.session_state.get('id_p_sel')):
        c1, c2 = st.columns([2, 1])
        bus_p = c1.text_input("🔍 Buscar proyecto, código o cliente...", key="bus_seg_v2")
        df_p_all = obtener_proyectos(bus_p)
        
        if supervisor_id and not df_p_all.empty:
            df_p_all = df_p_all[df_p_all['supervisor_id'] == supervisor_id]

        if not df_p_all.empty:
            opciones = {f"[{r['codigo']}] {r['proyecto_text']} - {r['cliente']}": r['id'] for _, r in df_p_all.iterrows()}
            sel_n = c2.selectbox("Seleccione Proyecto:", ["-- Seleccionar --"] + list(opciones.keys()))
            if sel_n != "-- Seleccionar --":
                st.session_state.id_p_sel = opciones[sel_n]
                st.session_state.p_nom_sel = sel_n

    if not st.session_state.get('id_p_sel'):
        st.info("💡 Seleccione un proyecto en el Bloque 1 para activar la matriz."); return

    id_p = st.session_state.id_p_sel

    # --- 1. BLOQUE 2: CONFIGURACIÓN Y HERRAMIENTAS (PLEGABLE) ---
    with st.expander("🛠️ BLOQUE 2: CONFIGURACIÓN AVANZADA Y HERRAMIENTAS", expanded=False):
        t1, t2, t3 = st.tabs(["⚖️ Ponderación", "🔍 Filtros", "📥 Importación Inteligente"])
        
        with t1:
            st.write("Peso porcentual de cada etapa (Suma = 100%):")
            cols_w = st.columns(4)
            pesos = {h: cols_w[i % 4].number_input(f"{h} (%)", value=12.5, step=0.5, key=f"p_{h}") for i, h in enumerate(HITOS_LIST)}
            if sum(pesos.values()) != 100: st.warning(f"Suma actual: {sum(pesos.values())}%")

        with t2:
            f1, f2, f3 = st.columns(3)
            agrupar_por = f1.selectbox("Agrupar matriz por:", ["Sin grupo", "Ubicación", "Tipo"])
            bus_c1 = f2.text_input("🔍 Filtro Primario:")
            bus_c2 = f3.text_input("🔍 Refinar Búsqueda:")

        with t3:
            f_av = st.file_uploader("Cargar Excel/CSV", type=["xlsx", "csv"])
            if f_av and st.button("🚀 Procesar Importación"):
                df_imp = pd.read_excel(f_av) if f_av.name.endswith('xlsx') else pd.read_csv(f_av)
                prods_db = obtener_productos_por_proyecto(id_p)
                for _, r_ex in df_imp.iterrows():
                    match = prods_db[(prods_db['ubicacion'].astype(str) == str(r_ex.get('Ubicacion',''))) & 
                                     (prods_db['tipo'].astype(str) == str(r_ex.get('Tipo','')))]
                    if not match.empty:
                        pid = match.iloc[0]['id']
                        # Buscamos el hito máximo con fecha en el excel
                        for h in reversed(HITOS_LIST):
                            f_ex = r_ex.get(h)
                            if pd.notnull(f_ex) and str(f_ex).strip() != "":
                                registrar_hitos_cascada(pid, h, str(f_ex))
                                break
                st.success("Importación completada."); st.rerun()

    # --- CARGA Y FILTRADO DE DATOS ---
    prods_all = obtener_productos_por_proyecto(id_p)
    if prods_all.empty: st.warning("El proyecto no tiene productos."); return
    
    # Filtros de Matriz
    df_f = prods_all.copy()
    if bus_c1: df_f = df_f[df_f['ubicacion'].str.contains(bus_c1, case=False) | df_f['tipo'].str.contains(bus_c1, case=False)]
    if bus_c2: df_f = df_f[df_f['ubicacion'].str.contains(bus_c2, case=False) | df_f['tipo'].str.contains(bus_c2, case=False)]

    # Carga de Seguimiento (Fix KeyError)
    segs_res = supabase.table("seguimiento").select("*").in_("producto_id", prods_all['id'].tolist()).execute()
    segs = pd.DataFrame(segs_res.data) if segs_res.data else pd.DataFrame(columns=['producto_id','hito','fecha','observaciones'])

    # --- 2. INDICADORES DE AVANCE ---
    def calc_avance(df_m, df_s):
        if df_m.empty: return 0.0
        # Filtrar hitos solo de los productos presentes
        df_s_f = df_s[df_s['producto_id'].isin(df_m['id'].tolist())]
        puntos = sum([pesos.get(h, 0) for h in df_s_f['hito']])
        return round(puntos / len(df_m), 2)

    pct_total = calc_avance(prods_all, segs)
    pct_parcial = calc_avance(df_f, segs)

    # --- 5. ACCIONES GLOBALES (CONTINUACIÓN) ---
    if col_g2.button("💾 GUARDAR AVANCE", type="primary", use_container_width=True):
        ahora = datetime.now()
        supabase.table("cierres_diarios").insert({"proyecto_id": id_p, "fecha": ahora.strftime("%d/%m/%Y"), "hora": ahora.strftime("%H:%M:%S")}).execute()
        supabase.table("proyectos").update({"avance": pct_total}).eq("id", id_p).execute()
        st.success("Guardado."); st.rerun()

    # Exportación (Estructura Seguimiento_Eliza.xlsx)
    df_exp = df_f.copy().rename(columns={'proyecto_id': 'Id Proyecto', 'ubicacion': 'Ubicacion', 'tipo': 'Tipo', 'ctd': 'Ctd'})
    for h in HITOS_LIST:
        df_exp[h] = df_exp['id'].apply(lambda x: segs[(segs['producto_id']==x) & (segs['hito']==h)]['fecha'].iloc[0] if not segs[(segs['producto_id']==x) & (segs['hito']==h)].empty else "")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_exp[['Id Proyecto', 'Ubicacion', 'Tipo', 'Ctd', 'ml'] + HITOS_LIST].to_excel(writer, index=False)
    col_g3.download_button("📥 EXPORTAR SEGUIMIENTO", data=output.getvalue(), file_name=f"Seguimiento_{id_p}.xlsx", use_container_width=True)

    # Indicadores visuales
    m1, m2 = st.columns(2)
    m1.markdown(f"<div class='metric-box'><b>% AVANCE TOTAL PROYECTO</b><br><h3>{pct_total}%</h3></div>", unsafe_allow_html=True)
    m2.markdown(f"<div class='metric-box'><b>% AVANCE SELECCIÓN</b><br><h3>{pct_parcial}%</h3></div>", unsafe_allow_html=True)

    # --- 3. MATRIZ CON STICKY HEADER ---
    st.markdown('<div class="sticky-top">', unsafe_allow_html=True)
    cols_h = st.columns([2.5] + [0.7]*8)
    cols_h[0].write("**Producto / Medida**")
    for i, hito in enumerate(HITOS_LIST):
        with cols_h[i+1]:
            st.write(MAPEO_HITOS[hito])
            if st.button("✅", key=f"all_{hito}"):
                for pid in df_f['id'].tolist(): registrar_hitos_cascada(pid, hito, fecha_reg.strftime("%d/%m/%Y"))
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # --- 4. ÁREA DE PRODUCTOS (SCROLL) ---
    st.markdown('<div class="scroll-area">', unsafe_allow_html=True)
    def render_matriz(df_r):
        rol = st.session_state.get('rol', 'Supervisor')
        for _, p in df_r.iterrows():
            cols = st.columns([2.5] + [0.7]*8)
            cols[0].write(f"**{p['ubicacion']}** {p['tipo']} ({p['ml']}ml)")
            for i, h in enumerate(HITOS_LIST):
                match = segs[(segs['producto_id'] == p['id']) & (segs['hito'] == h)]
                existe = not match.empty
                tiene_post = not segs[(segs['producto_id'] == p['id']) & (segs['hito'].isin(HITOS_LIST[i+1:]))].empty
                
                # Bloqueo Supervisor no desmarca. Admin no desmarca si hay posterior (Borrado en reversa).
                bloqueado = (existe and rol == "Supervisor") or tiene_post
                
                if cols[i+1].checkbox("", key=f"c_{p['id']}_{h}", value=existe, disabled=bloqueado, label_visibility="collapsed"):
                    if not existe:
                        registrar_hitos_cascada(p['id'], h, fecha_reg.strftime("%d/%m/%Y"))
                        st.rerun()
                elif existe and not bloqueado: # Lógica Desmarcado (8 a 1)
                    supabase.table("seguimiento").delete().eq("producto_id", p['id']).eq("hito", h).execute()
                    st.rerun()
    
    if agrupar_por != "Sin grupo":
        for n, g in df_f.groupby(agrupar_por.lower()):
            st.markdown(f"**📂 {n}**"); render_matriz(g)
    else: render_matriz(df_f)
    st.markdown('</div>', unsafe_allow_html=True)
