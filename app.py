import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_plotly_events import plotly_events

# 1. Configuración de página
st.set_page_config(page_title="Sistema Control PTAR", layout="wide", page_icon="💧")
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)
st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# 2. Función de limpieza de datos
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

# 3. Conexión y Carga de Datos
try:
    # Uso de la conexión actualizada para evitar errores de instalación
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_raw = conn.read(ttl=0)
    df_base = limpiar_datos_ptar(df_raw)

    # --- BARRA LATERAL (TUS FILTROS ORIGINALES) ---
    try:
        st.sidebar.image("logo-white-kenzo.png", use_container_width=True)
    except:
        st.sidebar.error("Logo no encontrado.")

    st.sidebar.header("Filtros de Análisis")
    
    if not df_base.empty and 'fecha' in df_base.columns:
        min_f, max_f = min(df_base['fecha']), max(df_base['fecha'])
        rango_fechas = st.sidebar.date_input("Rango de fechas:", [min_f, max_f])
        if len(rango_fechas) == 2:
            df_base = df_base[(df_base['fecha'] >= rango_fechas[0]) & (df_base['fecha'] <= rango_fechas[1])]

    if not df_base.empty and 'proceso' in df_base.columns:
        lista_p = sorted(df_base['proceso'].unique().tolist())
        procesos_sel = st.sidebar.multiselect("Selecciona el Proceso:", lista_p, default=lista_p)
        df_filtrado = df_base[df_base['proceso'].isin(procesos_sel)]
    else:
        df_filtrado = df_base

    # FILTRO DE BÚSQUEDA POR TEXTO (Se mantiene tal cual te gusta)
    if not df_filtrado.empty and 'quimicos' in df_filtrado.columns:
        busqueda_q = st.sidebar.text_input("🔍 Buscar Químico (escribe el nombre):", "")
        if busqueda_q:
            df_filtrado = df_filtrado[df_filtrado['quimicos'].astype(str).str.contains(busqueda_q, case=False, na=False)]

    # --- CUERPO PRINCIPAL ---
    t1, t2, t3 = st.tabs(["📊 Dashboard Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with t1:
        if not df_filtrado.empty:
            m1, m2, m3, m4 = st.columns(4)
            avg_ph = df_filtrado['ph'].mean()
            status_ph = "normal" if 6.0 <= avg_ph <= 9.0 else "inverse"
            m1.metric("Promedio pH", f"{avg_ph:.2f}", 
                      delta="EN NORMA" if status_ph == "normal" else "FUERA DE RANGO",
                      delta_color=status_ph)
            m2.metric("Temp Promedio", f"{df_filtrado['temp'].mean():.1f} °C")
            m3.metric("SST Promedio", f"{df_filtrado['sst'].mean():.2f}")
            m4.metric("Total Registros", len(df_filtrado))

            st.subheader("📈 Análisis de pH")
            fig_t = px.line(df_filtrado.sort_values('fecha'), x='fecha', y='ph', markers=True)
            fig_t.add_hline(y=9.0, line_dash="dash", line_color="red")
            fig_t.add_hline(y=6.0, line_dash="dash", line_color="red")
            st.plotly_chart(fig_t, use_container_width=True)

            st.subheader("📋 Detalle de Datos")
            st.dataframe(df_filtrado, use_container_width=True)
        else:
            st.warning("No hay datos para los filtros seleccionados.")

    with t2:
        st.info("Módulo de Agua Tratada en desarrollo.")

    with t3:
        st.subheader("🛠️ Bitácora de Mantenimiento Interactiva")
        st.markdown("Haz clic en una burbuja para ver el historial del equipo.")

        # Coordenadas que representan tu plano lateral
        equipos_data = {
            'Equipo': ['Homogeneización', 'Coagulación', 'Sedimentador', 'Oxidación', 'Filtración', 'Agua Tratada', 'Bomba B1', 'Bomba B2'],
            'X': [10, 28, 48, 65, 82, 95, 54, 63],
            'Y': [45, 35, 55, 45, 45, 35, 25, 25],
            'Estado': ['Al día', 'Próximo', 'Al día', 'Al día', 'Vencido', 'Al día', 'Al día', 'Próximo']
        }
        df_eq = pd.DataFrame(equipos_data)
        colores = {'Al día': '#00FF00', 'Próximo': '#FFFF00', 'Vencido': '#FF0000'}

        # Gráfico tipo plano nativo integrado
        fig_p = px.scatter(df_eq, x='X', y='Y', text='Equipo', color='Estado', 
                           color_discrete_map=colores, range_x=[0, 105], range_y=[0, 100])
        
        fig_p.update_traces(marker=dict(size=35, opacity=0.8, line=dict(width=2, color='white')),
                            textposition='top center', textfont=dict(size=13, color='white'))
        
        fig_p.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                            xaxis=dict(visible=False), yaxis=dict(visible=False),
                            showlegend=True, height=500)

        # Captura el clic del usuario
        clic = plotly_events(fig_p, click_event=True, override_height=500)

        if clic:
            idx = clic[0]['pointIndex']
            sel = df_eq.iloc[idx]['Equipo']
            st.markdown(f"### 📑 Historial: {sel}")
            # Simulación de tabla de historial
            df_hist = pd.DataFrame([{"Fecha": "2026-04-05", "Tarea": "Revisión rutinaria", "Técnico": "Luis M."}])
            st.table(df_hist)

except Exception as e:
    st.error(f"Error detectado: {e}")
