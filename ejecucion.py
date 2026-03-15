import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from base_datos import conectar, obtener_proyectos, obtener_gantt_real_data

def obtener_color_gradiente(avance):
    """Calcula el color hexadecimal entre Rojo, Amarillo y Verde según el avance."""
    avance = max(0, min(100, avance)) # Asegura que esté entre 0 y 100
    if avance < 50:
        r, g, b = 255, int((avance / 50) * 255), 0
    else:
        r, g, b = int(255 - ((avance - 50) / 50) * 255), 255, 0
    return f'rgb({r}, {g}, {b})'

def mostrar():
    st.header("📊 Cronograma de Ejecución V2")
    supabase = conectar()
    
    # --- 1. BUSCADOR ÚNICO Y SELECCIÓN ---
    with st.container(border=True):
        bus = st.text_input("🔍 Buscador Universal (Código, Nombre o Cliente)", placeholder="Ej: PTF-001 o Casa")
        df_p = obtener_proyectos(bus)
        
        if df_p.empty:
            st.info("No se encontraron coincidencias."); return
            
        dict_proy = {r['proyecto_display']: r['id'] for _, r in df_p.iterrows()}
        proyectos_sel = st.multiselect("Proyectos a visualizar:", options=list(dict_proy.keys()), default=list(dict_proy.keys())[:1])

    if proyectos_sel:
        data_final = []
        ORDEN_ETAPAS = ["Diseño", "Fabricación", "Traslado", "Instalación", "Entrega"]

        for p_nom in proyectos_sel:
            id_p = dict_proy[p_nom]
            res_p = supabase.table("proyectos").select("*").eq("id", id_p).execute()
            if not res_p.data: continue
            p_data = res_p.data[0]
            avance_p = p_data.get('avance', 0)

            # A. BARRAS PLANIFICADAS (GRISES)
            map_cols = [
                ("Diseño", 'p_dis_i', 'p_dis_f', "#D5D8DC"), # Gris Claro
                ("Fabricación", 'p_fab_i', 'p_fab_f', "#5D6D7E"), # Gris Oscuro
                ("Traslado", 'p_tra_i', 'p_tra_f', "#D5D8DC"),
                ("Instalación", 'p_ins_i', 'p_ins_f', "#D5D8DC"),
                ("Entrega", 'p_ent_i', 'p_ent_f', "#D5D8DC")
            ]
            for et, i_c, f_c, col in map_cols:
                if p_data.get(i_c) and p_data.get(f_c):
                    data_final.append(dict(Proyecto=p_nom, Etapa=et, Inicio=p_data[i_c], Fin=p_data[f_c], Color=col, Tipo="Planificado"))

            # B. BARRAS REALES (GRADIENTE)
            df_r = obtener_gantt_real_data(id_p)
            color_real = obtener_color_gradiente(avance_p)
            
            if not df_r.empty:
                for _, row in df_r.iterrows():
                    try:
                        str_f = str(row['fecha']).strip()
                        fecha_dt = datetime.strptime(str_f, '%d/%m/%Y') if "/" in str_f else datetime.strptime(str_f, '%Y-%m-%d')
                        # Mapeo de hitos a etapas
                        hito_l = row['hito'].lower()
                        et_m = "Instalación"
                        if "disen" in hito_l: et_m = "Diseño"
                        elif hito_l in ["corte", "canto", "perforado", "armado"]: et_m = "Fabricación"
                        elif "tras" in hito_l: et_m = "Traslado"
                        elif "entreg" in hito_l: et_m = "Entrega"

                        data_final.append(dict(Proyecto=p_nom, Etapa=et_m, Inicio=fecha_dt.strftime('%Y-%m-%d'), 
                                               Fin=(fecha_dt + timedelta(days=1)).strftime('%Y-%m-%d'), 
                                               Color=color_real, Tipo="Real"))
                    except: continue

        if not data_final:
            st.warning("Sin datos de fechas para mostrar."); return

        # GRÁFICO
        df_fig = pd.DataFrame(data_final)
        df_fig['Etapa'] = pd.Categorical(df_fig['Etapa'], categories=ORDEN_ETAPAS, ordered=True)
        
        fig = px.timeline(df_fig, x_start="Inicio", x_end="Fin", y="Etapa", color="Color",
                          facet_col="Proyecto", facet_col_wrap=1, color_discrete_map="identity")

        fig.update_yaxes(autorange="reversed")
        fig.update_layout(barmode='overlay', height=220 * len(proyectos_sel), showlegend=False, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)
