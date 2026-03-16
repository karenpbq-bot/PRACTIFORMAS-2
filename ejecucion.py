import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from base_datos import conectar, obtener_proyectos, obtener_datos_gantt_procesados

def calcular_color_semaforo(avance):
    """Devuelve el color matizado según el avance ponderado."""
    if avance < 50:
        # Rojo matizado
        intensidad = int(150 + (avance * 2.1)) 
        return f'rgb({intensidad}, 50, 50)'
    elif avance <= 75:
        # Amarillo matizado
        val = int((avance - 50) * 4)
        return f'rgb({200+val}, {200+val}, 0)'
    else:
        # Verde matizado
        intensidad = int(100 + ((avance - 75) * 4))
        return f'rgb(34, {intensidad}, 34)'

def mostrar():
    st.title("📊 Cronograma: Planificado vs. Ejecutado")
    
    # --- 1. BUSCADOR Y SELECCIÓN ---
    with st.sidebar:
        st.subheader("Filtros")
        bus_keyword = st.text_input("🔍 Buscar Proyecto", placeholder="Código o Nombre...")
        df_p = obtener_proyectos(bus_keyword)
        
        if df_p.empty:
            st.warning("No hay coincidencias.")
            return

        seleccionados = st.multiselect("Seleccionar Proyectos:", df_p['proyecto_display'].tolist())

    if not seleccionados:
        st.info("Selecciona proyectos en la barra lateral.")
        return

    # --- 2. CONSTRUCCIÓN DEL GRÁFICO ---
    # Definimos el orden de las etapas de abajo hacia arriba para que Diseño quede arriba
    ETAPAS_ORDEN = ["Entrega", "Instalación", "Traslado", "Fabricación", "Diseño"]
    
    fig = go.Figure()
    supabase = conectar()

    for i, p_display in enumerate(seleccionados):
        p_row = df_p[df_p['proyecto_display'] == p_display].iloc[0]
        id_p = p_row['id']
        res_p = supabase.table("proyectos").select("*").eq("id", id_p).execute()
        if not res_p.data: continue
        p_data = res_p.data[0]

        # Mapeo de columnas de la DB para lo planificado
        map_plan = {
            "Diseño": ("p_dis_i", "p_dis_f", "lightgrey"),
            "Fabricación": ("p_fab_i", "p_fab_f", "#4F4F4F"), # Gris Oscuro
            "Traslado": ("p_tra_i", "p_tra_f", "lightgrey"),
            "Instalación": ("p_ins_i", "p_ins_f", "lightgrey"),
            "Entrega": ("p_ent_i", "p_ent_f", "lightgrey")
        }

        datos_reales = obtener_datos_gantt_procesados(id_p)
        dict_reales = {d['Etapa']: d for d in datos_reales}

        for y_pos, etapa in enumerate(ETAPAS_ORDEN):
            # Posición base en el eje Y para cada etapa del proyecto actual
            # Multiplicamos por el índice del proyecto para separarlos físicamente
            base_y = (i * (len(ETAPAS_ORDEN) + 2)) + y_pos

            # --- A. BARRA PLANIFICADA (ARRIBA) ---
            ini_c, fin_c, col_p = map_plan[etapa]
            if p_data.get(ini_c) and p_data.get(fin_c):
                fig.add_trace(go.Bar(
                    base=[p_data[ini_c]],
                    x=[(pd.to_datetime(p_data[fin_c]) - pd.to_datetime(p_data[ini_c])).days],
                    y=[base_y + 0.2], # Desplazamiento hacia arriba
                    orientation='h',
                    name="Planificado",
                    marker_color=col_p,
                    hoverinfo="text",
                    text=f"<b>{p_display}</b><br>{etapa} Planificado<br>{p_data[ini_c]} a {p_data[fin_c]}",
                    width=0.35
                ))

            # --- B. BARRA EJECUTADA (ABAJO) ---
            if etapa in dict_reales:
                dr = dict_reales[etapa]
                color_sem = calcular_color_semaforo(dr['Avance'])
                fig.add_trace(go.Bar(
                    base=[dr['Inicio'].strftime('%Y-%m-%d')],
                    x=[(dr['Fin'] - dr['Inicio']).days if (dr['Fin'] - dr['Inicio']).days > 0 else 1],
                    y=[base_y - 0.2], # Desplazamiento hacia abajo
                    orientation='h',
                    name="Ejecutado",
                    marker_color=color_sem,
                    hoverinfo="text",
                    text=f"<b>{p_display}</b><br>{etapa} REAL<br>Avance: {round(dr['Avance'],1)}%<br>{dr['Inicio'].date()} a {dr['Fin'].date()}",
                    width=0.35
                ))

    # --- 3. AJUSTES DE FORMATO Y EJES ---
    fig.update_layout(
        barmode='overlay',
        showlegend=False,
        height=200 + (len(seleccionados) * 300),
        xaxis=dict(
            type='date',
            tickformat='%d %b', # Formato: Día y Mes (ej: 15 Mar)
            dtick="M1", # Marcas principales cada mes
            minor=dict(dtick=1000*60*60*24*14, showgrid=True, gridcolor="rgba(200,200,200,0.3)", griddash="dot"), # Quincenas
            gridcolor="rgba(150,150,150,0.5)"
        ),
        yaxis=dict(
            tickmode='array',
            tickvals=[(i * (len(ETAPAS_ORDEN) + 2)) + y for i in range(len(seleccionados)) for y in range(len(ETAPAS_ORDEN))],
            ticktext=ETAPAS_ORDEN * len(seleccionados),
            title=""
        ),
        margin=dict(l=150, r=20, t=50, b=50),
        plot_bgcolor="white"
    )

    # Añadir títulos de proyecto a la izquierda
    for i, p_display in enumerate(seleccionados):
        fig.add_annotation(
            x=0, y=(i * (len(ETAPAS_ORDEN) + 2)) + 2.5,
            xref="paper", yref="y",
            text=f"<b>{p_display}</b>",
            showarrow=False, font=dict(size=14, color="black"),
            xanchor="right", xshift=-100
        )

    st.plotly_chart(fig, use_container_width=True)
