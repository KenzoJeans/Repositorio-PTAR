import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_plotly_events import plotly_events
import numpy as np

# 1. Configuración de página y estilos corporativos
st.set_page_config(page_title="Sistema Control PTAR", layout="wide", page_icon="💧")
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)
st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# 2. Funciones de limpieza y lógica de datos
def limpiar_datos_ptar(df):
    if df is None or df.empty:
        return pd.DataFrame()
    df.columns = df.columns.str.strip()
    mapeo = {
        'ph': 'ph', 'pH': 'ph', 'PH': 'ph',
        'temp': 'temp', 'Temperatura': 'temp',
        'sst': 'sst', 'Solidos suspendidos': 'sst',
        'Fecha del reporte': 'fecha', 'fecha': 'fecha',
        'Proceso a reportar': 'proceso',
        'Productos quimicos utilizados en el proceso': 'quimicos'
    }
    df = df.rename(columns={k: v for k, v in mapeo.items() if k in df.columns})
    for col in ['ph', 'temp', 'sst']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce').dt.date
    return df.dropna(subset=['ph'])

# Lógica del Plano Interactivo (Mantenimiento)
def obtener_equipo_clic_plotly(x, y):
    """Retorna el nombre del equipo basado en las coordenadas del gráfico nativo"""
    # X de 0 a 100, Y de 0 a 100
    if 5 <= x <= 15 and 65 <= y <= 85: return "Tanque Homogeneización"
    if 25 <= x <= 35 and 15 <= y <= 35: return "Tanque Coagulación (Agitador)"
    if 40 <= x <= 50 and 45 <= y <= 65: return "Sedimentador"
    if 60 <= x <= 70 and 30 <= y <= 50: return "Tanque Oxidación"
    if 75 <= x <= 85 and 30 <= y <= 50: return "Sistema Filtración (Batería)"
    if 85 <= x <= 95 and 10 <= y <= 30: return "Tanque Agua Tratada"
    if 51 <= x <= 56 and 69 <= y <= 74: return "Bomba B1"
    if 61 <= x <= 66 and 69 <= y <= 74: return "Bomba B2"
    return None

# 3. Conexión y Carga de Datos
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_raw = conn.read(ttl=0)
    df_base = limpiar_datos_ptar(df_raw)

    # --- BARRA LATERAL (LOGO Y FILTROS) ---
    try:
        st.sidebar.image("logo_kenzo.png", use_container_width=True)
    except:
        st.sidebar.error("Error: Logo no encontrado. Verifica el nombre en GitHub.")

    st.sidebar.header("Filtros de Análisis")
    
    # Filtro de Fecha
    if not df_base.empty and 'fecha' in df_base.columns:
        min_f, max_f = min(df_base['fecha']), max(df_base['fecha'])
        rango_fechas = st.sidebar.date_input("Rango de fechas:", [min_f, max_f])
        if len(rango_fechas) == 2:
            df_base = df_base[(df_base['fecha'] >= rango_fechas[0]) & (df_base['fecha'] <= rango_fechas[1])]

    # Filtro de Proceso (Multiselect)
    if not df_base.empty and 'proceso' in df_base.columns:
        lista_p = sorted(df_base['proceso'].unique().tolist())
        procesos_sel = st.sidebar.multiselect("Selecciona el Proceso:", lista_p, default=lista_p)
        df_filtrado = df_base[df_base['proceso'].isin(procesos_sel)]
    else:
        df_filtrado = df_base

    # --- FILTRO POR BÚSQUEDA DE TEXTO (QUÍMICOS) ---
    if not df_filtrado.empty and 'quimicos' in df_filtrado.columns:
        busqueda_q = st.sidebar.text_input("🔍 Buscar Químico (escribe el nombre):", "")
        if busqueda_q:
            df_filtrado = df_filtrado[df_filtrado['quimicos'].astype(str).str.contains(busqueda_q, case=False, na=False)]

    # --- CUERPO PRINCIPAL ---
    t1, t2, t3 = st.tabs(["📊 Dashboard Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento NATIVO"])

    with t1:
        if not df_filtrado.empty:
            # Métricas
            m1, m2, m3, m4 = st.columns(4)
            avg_ph = df_filtrado['ph'].mean()
            status_ph = "normal" if 6.0 <= avg_ph <= 9.0 else "inverse"
            m1.metric("Promedio pH", f"{avg_ph:.2f}", 
                      delta="EN NORMA" if status_ph == "normal" else "FUERA DE RANGO",
                      delta_color=status_ph)
            m2.metric("Temp Promedio", f"{df_filtrado['temp'].mean():.1f} °C")
            m3.metric("SST Promedio", f"{df_filtrado['sst'].mean():.2f}")
            m4.metric("Total Registros", len(df_filtrado))

            # Gráfica de pH
            st.subheader("📈 Análisis de pH")
            fig_t = px.line(df_filtrado.sort_values('fecha'), x='fecha', y='ph', markers=True, title="Evolución de pH")
            fig_t.add_hline(y=9.0, line_dash="dash", line_color="red")
            fig_t.add_hline(y=6.0, line_dash="dash", line_color="red")
            st.plotly_chart(fig_t, use_container_width=True)

            # Tabla de Datos
            st.subheader("📋 Detalle de Datos")
            st.dataframe(df_filtrado, use_container_width=True)
        else:
            st.warning("No hay datos para los filtros seleccionados.")

    with t2:
        st.info("Módulo de Agua Tratada en desarrollo.")

    # --- T3: MANTENIMIENTO NATIVO (PLANO INTEGRADO) ---
    with t3:
        st.subheader("🛠️ Bitácora de Mantenimiento Integrada")
        st.markdown("Haz clic sobre una unidad o equipo en el plano lateral de la PTAR para ver su historial.")

        # -- DATOS SIMULADOS PARA PUNTOS DE INTERACCIÓN --
        equipos_coord = {
            'Equipo': ['Tanque Homogeneización', 'Tanque Coagulación (Agitador)', 'Sedimentador', 'Tanque Oxidación', 'Sistema Filtración (Batería)', 'Tanque Agua Tratada', 'Bomba B1', 'Bomba B2'],
            'X': [10, 30, 45, 65, 80, 90, 53.5, 63.5],
            'Y': [75, 25, 55, 40, 40, 20, 71.5, 71.5],
            'Estado': ['Al día', 'Próximo', 'Al día', 'Al día', 'Vencido', 'Al día', 'Al día', 'Próximo']
        }
        df_equipos = pd.DataFrame(equipos_coord)
        
        # Mapeo de colores por estado (verde, amarillo, rojo)
        map_colores = {'Al día': 'lime', 'Próximo': 'yellow', 'Vencido': 'red'}
        df_equipos['Color'] = df_equipos['Estado'].map(map_colores)

        # -- CREACIÓN DEL PLANO NATIVO CON PLOTLY --
        # Usamos una gráfica de dispersión como layout del plano
        fig_plano_nativo = px.scatter(df_equipos, x='X', y='Y', text='Equipo', color='Estado',
                                      color_discrete_map=map_colores, size=[15]*len(df_equipos),
                                      title="Distribución de la Planta (Plano Nátivo Integrado)")

        # Configuración estética para fondo transparente e integrado
        fig_plano_nativo.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',   # Fondo transparente
            plot_bgcolor='rgba(0,0,0,0)',    # Fondo transparente
            showlegend=False,
            margin=dict(l=0, r=0, t=30, b=0),
            xaxis=dict(showgrid=False, zeroline=False, visible=False, range=[0, 100]),
            yaxis=dict(showgrid=False, zeroline=False, visible=False, range=[0, 100])
        )
        
        # Ajustes de las burbujas (más transparentes, texto más claro)
        fig_plano_nativo.update_traces(
            textposition='top center', 
            textfont=dict(color='lightgrey', size=11),
            marker=dict(line=dict(color='lightgrey', width=1), opacity=0.8)
        )

        # -- CAPTURA DE CLIC (NATIVO) --
        # Esta captura funciona sobre los puntos de Plotly, no sobre la imagen pegada
        selected_point_nativo = plotly_events(fig_plano_nativo, click_event=True, override_height=300)

        equipo_seleccionado_nativo = None
        if selected_point_nativo:
            # Obtenemos el nombre del equipo de la tabla basada en el punto clickeado
            index_clic = selected_point_nativo[0]['pointIndex']
            equipo_seleccionado_nativo = df_equipos.iloc[index_clic]['Equipo']
            
        # -- MOSTRAR HISTORIAL --
        if equipo_seleccionado_nativo:
            st.markdown(f"**### Historial para: {equipo_seleccionado_nativo}**")
            
            # Simulamos bitácora
            historial_simulado_nativo = {
                "Tanque Homogeneización": [{"Fecha": "2026-03-01", "Actividad": "Limpieza lodos", "Responsable": "Luis M."}, {"Fecha": "2026-01-15", "Actividad": "Ajuste sensor pH", "Responsable": "Jorge P."}],
                "Bomba B1": [{"Fecha": "2026-03-10", "Actividad": "Cambio sellos", "Responsable": "Técnico Ext."}],
                "Sistema Filtración (Batería)": [{"Fecha": "2025-11-20", "Actividad": "Limpieza de medios filtrantes", "Responsable": "Luis M."}]
            }
            
            if equipo_seleccionado_nativo in historial_simulado_nativo:
                df_h = pd.DataFrame(historial_simulado_nativo[equipo_seleccionado_nativo])
                st.dataframe(df_h, use_container_width=True)
            else:
                st.info("No se registran actividades de mantenimiento para este equipo.")
        else:
            st.info("Haz clic en un punto de equipo del plano nativo (burbujas Verdes/Amarillas/Rojas) para iniciar.")

except Exception as e:
    st.error(f"Se detectó un error crítico: {e}")
