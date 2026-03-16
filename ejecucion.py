import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from base_datos import conectar, obtener_proyectos, obtener_gantt_real_data

# =========================================================
# 1. CONFIGURACIÓN Y FUNCIÓN DE COLOR DINÁMICO
# =========================================================
ORDEN_ETAPAS = ["Diseño", "Fabricación", "Traslado", "Instalación", "Entrega"]

def obtener_color_semaforo(avance):
    """Calcula el color con matices según el % de avance."""
    if avance < 50:
        # Rojo matizado: más oscuro cuanto menos avance
        val = int(100 + (avance * 2))
        return f'rgb({val}, 0, 0)'
    elif avance <= 75:
        # Amarillo/Naranja matizado
        val = int(150 + (avance - 50) * 4)
        return f'rgb({val}, {val}, 0)'
    else:
        # Verde matizado: más brillante al llegar al 100%
        val = int(100 + (avance - 75) * 6)
        return f'rgb(0, {val}, 0)'

def mostrar():
    st.header("📊 Tablero de Control: Planificado vs. Real")
    supabase = conectar()
    
    with st.sidebar:
        st.divider()
        st.subheader("Opciones de Visualización")
        solo_real = st.toggle("Ocultar Planificación", value=False)
    
    with st.container(border=True):
        bus = st.text_input("🔍 Localizador de Proyectos", placeholder="Código, Cliente o Nombre...")
        df_p = obtener_proyectos(bus)
        
        if df_p.empty:
            st.info("No se encontraron coincidencias."); return
            
        dict_proy = {f"{r['proyecto_text']} — {r['cliente']}": r['id'] for _, r in df_p.iterrows()}
        
    proyectos_sel = st.multiselect("Proyectos a Auditar:", 
                                    options=list(dict_proy.keys()), 
                                    default=list(dict_proy.keys())[:1])

    if proyectos_sel:
        data_final = []
        
        for p_nom in proyectos_sel:
            id_p = dict_proy[p_nom]
            res_p = supabase.table("proyectos").select("*").eq("id", id_p).execute()
            if not res_p.data: continue
            p_data = res_p.data[0]
            
            # --- CÁLCULO DE AVANCE PARA COLORES ---
            # Obtenemos el avance actual del proyecto para usarlo en el color real
            avance_p = p_data.get('avance', 0)
            color_dinamico = obtener_color_semaforo(avance_p)

            # A. DATA PLANIFICADA (BARRAS GRISES - ESQUELETO)
            if not solo_real:
                map_cols = [
                    ("Diseño", 'p_dis_i', 'p_dis_f', "#BDC3C7"), # Gris Perla
                    ("Fabricación", 'p_fab_i', 'p_fab_f', "#5D6D7E"), # Gris Industrial
                    ("Traslado", 'p_tra_i', 'p_tra_f', "#BDC3C7"),
                    ("Instalación", 'p_ins_i', 'p_ins_f', "#BDC3C7"),
                    ("Entrega", 'p_ent_i', 'p_ent_f', "#BDC3C7")
                ]
                for et, i_c, f_c, col in map_cols:
                    if p_data.get(i_c) and p_data.get(f_c):
                        data_final.append(dict(
                            Proyecto=p_nom, Etapa=et, Inicio=p_data[i_c], 
                            Fin=p_data[f_c], Color=col, Tipo="Planificado"
                        ))
            
            # B. DATA REAL (MAPEO DE HITOS)
            df_r = obtener_gantt_real_data(id_p)
            if not df_r.empty:
                for _, row in df_r.iterrows():
                    try:
                        str_f = str(row['fecha']).strip()
                        fecha_dt = datetime.strptime(str_f, '%d/%m/%Y') if "/" in str_f else datetime.strptime(str_f, '%Y-%m-%d')
                        
                        # Mapeo a las 5 etapas
                        hito_l = row['hito'].lower()
                        if "disen" in hito_l: et_m = "Diseño"
                        elif any(x in hito_l for x in ["fabric", "corte", "armad"]): et_m = "Fabricación"
                        elif "tras" in hito_l or "obra" in hito_l: et_m = "Traslado"
                        elif "entreg" in hito_l: et_m = "Entrega"
                        else: et_m = "Instalación"
                        
                        data_final.append(dict(
                            Proyecto=p_nom, Etapa=et_m, Inicio=fecha_dt.strftime('%Y-%m-%d'), 
                            Fin=(fecha_dt + timedelta(days=2)).strftime('%Y-%m-%d'), 
                            Color=color_dinamico, Tipo="Real"
                        ))
                    except: continue

        if not data_final:
            st.warning("No hay datos suficientes."); return

        # --- CONSTRUCCIÓN DEL GRÁFICO ---
        df_fig = pd.DataFrame(data_final)
        
        # 1. Forzamos el orden de las etapas (Diseño arriba)
        df_fig['Etapa'] = pd.Categorical(df_fig['Etapa'], categories=ORDEN_ETAPAS, ordered=True)
        df_fig = df_fig.sort_values(['Proyecto', 'Etapa'], ascending=[True, False])
        
        fig = px.timeline(
            df_fig, x_start="Inicio", x_end="Fin", y="Etapa", color="Color",
            facet_col="Proyecto", facet_col_wrap=1,
            color_discrete_map="identity", category_orders={"Etapa": ORDEN_ETAPAS}
        )

        # 2. CORRECCIÓN DE ORDEN Y RANGO (MES A MES)
        # Forzamos que el eje Y no se invierta
        fig.update_yaxes(autorange="reversed", showgrid=True, gridcolor='rgba(128,128,128,0.2)')

        # Ajuste de rango de 4 meses para ver todo el planificado
        f_min = pd.to_datetime(df_fig['Inicio']).min()
        f_max = f_min + timedelta(days=120)

        fig.update_xaxes(
            range=[f_min, f_max],
            dtick="M1",            # Una marca por mes
            tickformat="%b %Y",    # Mar 2026
            showgrid=True, 
            gridcolor='rgba(128,128,128,0.3)', 
            griddash='dot'
        )

        fig.update_layout(
            barmode='group',       # Barras una debajo de otra por etapa
            height=450 * len(proyectos_sel), 
            margin=dict(l=10, r=10, t=50, b=10),
            showlegend=False,
            bargap=0.3
        )

        # Resaltado de barras
        fig.update_traces(marker_line_color="white", marker_line_width=1, opacity=0.9)

        # Línea de fecha actual
        fig.add_vline(x=datetime.now().timestamp() * 1000, line_width=2, line_dash="dash", line_color="red")

        st.plotly_chart(fig, use_container_width=True)
