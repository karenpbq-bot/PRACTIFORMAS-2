import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from base_datos import conectar, obtener_proyectos, obtener_gantt_real_data

ORDEN_ETAPAS = ["Diseño", "Fabricación", "Traslado", "Instalación", "Entrega"]

COLORES_REALES = {
    "Diseño": "#1ABC9C",      # Turquesa
    "Fabricación": "#F39C12", # Naranja
    "Traslado": "#9B59B6",    # Morado
    "Instalación": "#2E86C1", # Azul
    "Entrega": "#27AE60"      # Verde
}

def mostrar():
    st.header("📊 Cronograma Global de Ejecución")
    supabase = conectar()
    
    with st.sidebar:
        st.divider()
        st.subheader("Configuración de Visualización")
        solo_real = st.toggle("Ver solo ejecución real", value=False)
    
    with st.container(border=True):
        bus = st.text_input("🔍 Buscar por Proyecto o Cliente...", placeholder="Ej: Casa")
        df_p = obtener_proyectos(bus)
        
        if df_p.empty:
            st.info("No se encontraron proyectos activos."); return
            
        dict_proy = {f"{r['proyecto_text']} — {r['cliente']}": r['id'] for _, r in df_p.iterrows()}
        
    proyectos_sel = st.multiselect("Visualizar Proyectos:", 
                                    options=list(dict_proy.keys()), 
                                    default=list(dict_proy.keys())[:1])

    if proyectos_sel:
        data_final = []
        fecha_minima_global = datetime.now() # Para fijar el inicio del gráfico

        for p_nom in proyectos_sel:
            id_p = dict_proy[p_nom]
            res_p = supabase.table("proyectos").select("*").eq("id", id_p).execute()
            if not res_p.data: continue
            p_data = res_p.data[0]
            
            # Guardamos la fecha de inicio del proyecto para el rango del gráfico
            if p_data.get('p_dis_i'):
                f_ini_p = pd.to_datetime(p_data['p_dis_i'])
                if f_ini_p < fecha_minima_global: fecha_minima_global = f_ini_p

            if not solo_real:
                map_cols = [
                    ("Diseño", 'p_dis_i', 'p_dis_f', "#EBEDEF"),
                    ("Fabricación", 'p_fab_i', 'p_fab_f', "#7F8C8D"),
                    ("Traslado", 'p_tra_i', 'p_tra_f', "#EBEDEF"),
                    ("Instalación", 'p_ins_i', 'p_ins_f', "#EBEDEF"),
                    ("Entrega", 'p_ent_i', 'p_ent_f', "#EBEDEF")
                ]
                for et, i_c, f_c, col in map_cols:
                    if p_data.get(i_c) and p_data.get(f_c):
                        data_final.append(dict(
                            Proyecto=p_nom, Etapa=et, Inicio=p_data[i_c], 
                            Fin=p_data[f_c], Color=col, Tipo="Planificado"
                        ))
            
            df_r = obtener_gantt_real_data(id_p)
            if not df_r.empty:
                for _, row in df_r.iterrows():
                    try:
                        str_f = str(row['fecha']).strip()
                        fecha_dt = datetime.strptime(str_f, '%d/%m/%Y') if "/" in str_f else datetime.strptime(str_f, '%Y-%m-%d')
                        inicio_real = fecha_dt.strftime('%Y-%m-%d')
                        fin_real = (fecha_dt + timedelta(days=2)).strftime('%Y-%m-%d') # Un poco más ancha para que se vea
                        
                        # Mapeo mejorado para asegurar que caigan en las 5 etapas
                        hito_l = row['hito'].lower()
                        if "disen" in hito_l: et_match = "Diseño"
                        elif any(x in hito_l for x in ["fabric", "corte", "canto", "armad"]): et_match = "Fabricación"
                        elif "tras" in hito_l or "obra" in hito_l: et_match = "Traslado"
                        elif "entreg" in hito_l or "revisi" in hito_l: et_match = "Entrega"
                        else: et_match = "Instalación"
                        
                        data_final.append(dict(
                            Proyecto=p_nom, Etapa=et_match, Inicio=inicio_real, 
                            Fin=fin_real, Color=COLORES_REALES.get(et_match, "#2E86C1"), Tipo="Real"
                        ))
                    except: continue

        if not data_final:
            st.warning("No hay datos para mostrar."); return

        df_fig = pd.DataFrame(data_final)
        df_fig['Etapa'] = pd.Categorical(df_fig['Etapa'], categories=ORDEN_ETAPAS, ordered=True)
        df_fig = df_fig.sort_values(['Proyecto', 'Etapa', 'Tipo'], ascending=[True, False, True])
        
        fig = px.timeline(
            df_fig, x_start="Inicio", x_end="Fin", y="Etapa", color="Color",
            facet_col="Proyecto", facet_col_wrap=1,
            color_discrete_map="identity", 
            category_orders={"Etapa": ORDEN_ETAPAS},
            hover_data=["Tipo"]
        )

        # AJUSTES CRÍTICOS PARA VER LAS 5 ETAPAS Y 4 MESES
        fig.update_yaxes(autorange="reversed", showgrid=True)

        # 1. Fijar rango de 4 meses y marcas mensuales
        fecha_fin_vista = fecha_minima_global + timedelta(days=120)
        fig.update_xaxes(
            range=[fecha_minima_global, fecha_fin_vista], # Rango forzado de 4 meses
            dtick="M1",            # Una marca por mes
            tickformat="%b %Y",    # Formato: Mar 2024
            showgrid=True, 
            gridcolor='LightGray', 
            griddash='dot'
        )

        fig.update_layout(
            barmode='group',       # CAMBIO CLAVE: 'group' pone una barra junto a la otra (no encima)
            height=400 * len(proyectos_sel), # Más alto para que quepan las barras agrupadas
            margin=dict(l=10, r=10, t=30, b=10),
            showlegend=False,
            bargap=0.2
        )

        # Línea de HOY
        fig.add_vline(x=datetime.now().timestamp() * 1000, line_width=2, line_dash="dash", line_color="red")

        st.plotly_chart(fig, use_container_width=True)
