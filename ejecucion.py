import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from base_datos import conectar, obtener_proyectos, obtener_datos_gantt_procesados

def calcular_color_semaforo(avance):
    """Calcula el color matizado según el avance ponderado (Rojo-Amarillo-Verde)."""
    if avance < 50:
        # Rojo: De oscuro (poco avance) a más claro
        intensidad = int(150 + (avance * 2.1)) 
        return f'rgb({intensidad}, 50, 50)'
    elif avance <= 75:
        # Amarillo: De ocre a brillante
        val = int((avance - 50) * 4)
        return f'rgb({200+val}, {200+val}, 0)'
    else:
        # Verde: De lima a bosque (oscuro al llegar al 100)
        intensidad = int(100 + ((avance - 75) * 4))
        return f'rgb(34, {intensidad}, 34)'

def mostrar():
    st.title("📊 Cronograma: Planificado vs. Ejecutado")
    
    # --- 1. BUSCADOR Y SELECCIÓN EN BARRA LATERAL ---
    with st.sidebar:
        st.subheader("Filtros de Visualización")
        bus_keyword = st.text_input("🔍 Buscar Proyecto", placeholder="Código, Cliente o Nombre...")
        df_p = obtener_proyectos(bus_keyword)
        
        if df_p.empty:
            st.warning("No hay proyectos que coincidan."); return

        seleccionados = st.multiselect("Proyectos a visualizar:", df_p['proyecto_display'].tolist())
        
        st.divider()
        # NUEVO FILTRO: Ver solo ejecutados
        ver_solo_ejecutado = st.toggle("Ver solo barras ejecutadas", value=False)

    if not seleccionados:
        st.info("💡 Selecciona uno o más proyectos en la barra lateral para generar el gráfico comparativo."); return

    # --- 2. CONFIGURACIÓN DEL GRÁFICO ---
    # Orden de etapas: Diseño arriba, Entrega abajo
    ETAPAS_ORDEN = ["Entrega", "Instalación", "Traslado", "Fabricación", "Diseño"]
    fig = go.Figure()
    supabase = conectar()

    for i, p_display in enumerate(seleccionados):
        # Obtener datos del proyecto desde la base de datos
        p_row = df_p[df_p['proyecto_display'] == p_display].iloc[0]
        id_p = p_row['id']
        res_p = supabase.table("proyectos").select("*").eq("id", id_p).execute()
        if not res_p.data: continue
        p_data = res_p.data[0]

        # Mapeo de columnas planificadas
        map_plan = {
            "Diseño": ("p_dis_i", "p_dis_f", "#D3D3D3"), # Gris Claro
            "Fabricación": ("p_fab_i", "p_fab_f", "#4F4F4F"), # Gris Oscuro
            "Traslado": ("p_tra_i", "p_tra_f", "#D3D3D3"),
            "Instalación": ("p_ins_i", "p_ins_f", "#D3D3D3"),
            "Entrega": ("p_ent_i", "p_ent_f", "#D3D3D3")
        }

        # Obtener datos reales procesados desde base_datos.py
        datos_reales = obtener_datos_gantt_procesados(id_p)
        dict_reales = {d['Etapa']: d for d in datos_reales}

        for y_pos, etapa in enumerate(ETAPAS_ORDEN):
            # Posición base en el eje Y para separar proyectos y etapas
            base_y = (i * (len(ETAPAS_ORDEN) + 2)) + y_pos

            # --- A. BARRA PLANIFICADA (ARRIBA - GRIS) ---
            if not ver_solo_ejecutado:
                ini_c, fin_c, col_p = map_plan[etapa]
                if p_data.get(ini_c) and p_data.get(fin_c):
                    # Calculamos duración en días
                    duracion = (pd.to_datetime(p_data[fin_c]) - pd.to_datetime(p_data[ini_c])).days
                    fig.add_trace(go.Bar(
                        base=[p_data[ini_c]],
                        x=[max(1, duracion)],
                        y=[base_y + 0.22], # Desplazamiento hacia arriba
                        orientation='h',
                        marker_color=col_p,
                        hoverinfo="text",
                        text=f"<b>{p_display}</b><br>{etapa} (Planificado)<br>{p_data[ini_c]} al {p_data[fin_c]}",
                        width=0.4
                    ))

            # --- B. BARRA EJECUTADA (ABAJO - COLOR MATIZADO) ---
            if etapa in dict_reales:
                dr = dict_reales[etapa]
                color_sem = calcular_color_semaforo(dr['Avance'])
                duracion_real = (dr['Fin'] - dr['Inicio']).days
                
                fig.add_trace(go.Bar(
                    base=[dr['Inicio'].strftime('%Y-%m-%d')],
                    x=[max(1, duracion_real)],
                    y=[base_y - 0.22] if not ver_solo_ejecutado else [base_y], # Centrado si solo es ejecutado
                    orientation='h',
                    marker_color=color_sem,
                    hoverinfo="text",
                    text=f"<b>{p_display}</b><br>{etapa} (REAL)<br>Avance Ponderado: {round(dr['Avance'],1)}%<br>{dr['Inicio'].date()} al {dr['Fin'].date()}",
                    width=0.4 if not ver_solo_ejecutado else 0.7
                ))

    # --- 3. AJUSTES DE FORMATO ---
    fig.update_layout(
        barmode='overlay',
        showlegend=False,
        height=250 + (len(seleccionados) * 350),
        xaxis=dict(
            type='date',
            tickformat='%d %b', # Día y Mes (Ej: 15 Mar)
            dtick="M1", 
            minor=dict(dtick=1000*60*60*24*14, showgrid=True, gridcolor="rgba(200,200,200,0.2)", griddash="dot"), # Quincenas
            gridcolor="rgba(150,150,150,0.4)"
        ),
        yaxis=dict(
            tickmode='array',
            tickvals=[(i * (len(ETAPAS_ORDEN) + 2)) + y for i in range(len(seleccionados)) for y in range(len(ETAPAS_ORDEN))],
            ticktext=ETAPAS_ORDEN * len(seleccionados),
            title=""
        ),
        margin=dict(l=150, r=20, t=80, b=50),
        plot_bgcolor="white"
    )

    # Anotaciones con los nombres de los proyectos a la izquierda
    for i, p_display in enumerate(seleccionados):
        fig.add_annotation(
            x=0, y=(i * (len(ETAPAS_ORDEN) + 2)) + 2,
            xref="paper", yref="y",
            text=f"<b>PROYECTO: {p_display}</b>",
            showarrow=False, font=dict(size=14, color="#002147"),
            xanchor="right", xshift=-110
        )

    st.plotly_chart(fig, use_container_width=True)
