import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from base_datos import conectar, obtener_proyectos, obtener_datos_gantt_procesados

# =========================================================
# 1. LÓGICA VISUAL: SEMÁFORO GERENCIAL
# =========================================================
def obtener_color_estricto(avance):
    """Devuelve el color matizado según el avance ponderado real."""
    if avance < 50:
        # Rojo: De fuerte a naranja
        return f'rgb({int(180 + avance)}, 60, 60)'
    elif avance <= 75:
        # Amarillo: De ocre a brillante
        return f'rgb({int(200 + (avance-50)*2)}, {int(180 + (avance-50)*2)}, 0)'
    else:
        # Verde: De lima a bosque sólido
        return f'rgb(40, {int(120 + (avance-75)*4)}, 40)'

def mostrar():
    st.title("📊 Control de Ejecución: Planificado vs. Real")
    
    # --- A. FILTROS Y SELECCIÓN ---
    with st.sidebar:
        st.subheader("🔍 Filtros de Auditoría")
        bus_keyword = st.text_input("Buscador de Proyectos", placeholder="Código, Cliente, Nombre...")
        df_p = obtener_proyectos(bus_keyword)
        
        if df_p.empty:
            st.warning("No se encontraron coincidencias."); return

        proyectos_selec = st.multiselect("Seleccione Proyectos para Comparar", df_p['proyecto_display'].tolist())
        
        st.divider()
        st.write("⚙️ **Ajustes de Vista**")
        ver_solo_real = st.checkbox("Ocultar Planificación (Ver solo Real)", value=False)

    if not proyectos_selec:
        st.info("💡 Seleccione uno o más proyectos en el buscador lateral para visualizar el cronograma."); return

    # --- B. CONFIGURACIÓN DEL GRÁFICO ---
    ETAPAS = ["Diseño", "Fabricación", "Traslado", "Instalación", "Entrega"]
    ETAPAS_REVERSA = ETAPAS[::-1] # Inversión para que Diseño quede arriba
    
    fig = go.Figure()
    supabase = conectar()

    for i, p_display in enumerate(proyectos_selec):
        p_row = df_p[df_p['proyecto_display'] == p_display].iloc[0]
        id_p = p_row['id']
        
        # Recuperamos fechas del contrato/plan desde la tabla proyectos
        res_p = supabase.table("proyectos").select("*").eq("id", id_p).execute()
        if not res_p.data: continue
        p_data = res_p.data[0]

        # Recuperamos avance real (procesado por base_datos.py en las 5 etapas)
        datos_reales = obtener_datos_gantt_procesados(id_p)
        dict_reales = {d['Etapa']: d for d in datos_reales}

        for y_idx, etapa in enumerate(ETAPAS_REVERSA):
            # Posicionamiento absoluto para evitar solapamientos
            pos_y = (i * (len(ETAPAS) * 3)) + (y_idx * 2)

            # --- 1. GANTT PLANIFICADO (BARRA SUPERIOR - GRIS) ---
            if not ver_solo_real:
                map_fechas = {
                    "Diseño": ("p_dis_i", "p_dis_f"), "Fabricación": ("p_fab_i", "p_fab_f"),
                    "Traslado": ("p_tra_i", "p_tra_f"), "Instalación": ("p_ins_i", "p_ins_f"),
                    "Entrega": ("p_ent_i", "p_ent_f")
                }
                f_i, f_f = map_fechas[etapa]
                
                if p_data.get(f_i) and p_data.get(f_f):
                    color_plan = "#4F4F4F" if etapa == "Fabricación" else "#D3D3D3"
                    fig.add_trace(go.Bar(
                        base=[p_data[f_i]],
                        x=[(pd.to_datetime(p_data[f_f]) - pd.to_datetime(p_data[f_i])).days],
                        y=[pos_y + 0.4],
                        orientation='h',
                        marker_color=color_plan,
                        name="Planificado",
                        hoverinfo="text",
                        text=f"PLAN: {etapa} - {p_display}",
                        width=0.4
                    ))

            # --- 2. GANTT EJECUTADO (BARRA INFERIOR - SEMÁFORO) ---
            if etapa in dict_reales:
                dr = dict_reales[etapa]
                avance = round(dr['Avance'], 1)
                color_real = obtener_color_estricto(avance)
                
                fig.add_trace(go.Bar(
                    base=[dr['Inicio'].strftime('%Y-%m-%d')],
                    x=[(dr['Fin'] - dr['Inicio']).days + 1],
                    y=[pos_y - 0.4] if not ver_solo_real else [pos_y],
                    orientation='h',
                    marker_color=color_real,
                    text=f"{avance}%", 
                    textposition="inside",
                    textfont=dict(color="white", size=10),
                    name="Ejecutado",
                    hoverinfo="text",
                    hovertext=f"REAL: {etapa}<br>Inicio: {dr['Inicio'].date()}<br>Fin: {dr['Fin'].date()}<br>Avance: {avance}%",
                    width=0.6 if not ver_solo_real else 1.2
                ))

    # --- C. AJUSTES DE ESCALA TEMPORAL (MES A MES) ---
    fig.update_layout(
        barmode='overlay',
        showlegend=False,
        plot_bgcolor="white",
        height=250 + (len(proyectos_selec) * 400),
        xaxis=dict(
            type='date',
            tickformat='%b %Y', # Formato: Mar 2026
            dtick="M1",         # MARCA PRINCIPAL: CADA MES
            gridcolor="#EEEEEE",
            minor=dict(
                dtick=1000*60*60*24*14, # MARCA SECUNDARIA: CADA 14 DÍAS (QUINCENA)
                showgrid=True, 
                gridcolor="#F5F5F5", 
                griddash="dot"
            )
        ),
        yaxis=dict(
            tickmode='array',
            tickvals=[(i * (len(ETAPAS) * 3)) + (y * 2) for i in range(len(proyectos_selec)) for y in range(len(ETAPAS))],
            ticktext=ETAPAS_REVERSA * len(proyectos_selec),
            fixedrange=True
        ),
        margin=dict(l=200, r=50, t=100, b=50)
    )

    # Títulos de Proyecto en el eje vertical
    for i, p_display in enumerate(proyectos_selec):
        fig.add_annotation(
            x=-0.01, y=(i * (len(ETAPAS) * 3)) + (len(ETAPAS) - 1),
            xref="paper", yref="y",
            text=f"<b>PROYECTO: {p_display.upper()}</b>",
            showarrow=False, xanchor="right", font=dict(size=14, color="#002147")
        )

    st.plotly_chart(fig, use_container_width=True)
