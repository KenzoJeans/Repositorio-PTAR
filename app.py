import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_plotly_events import plotly_events

# 1. Configuración de página
st.set_page_config(page_title="Sistema Control PTAR", layout="wide", page_icon="💧")
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)
st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# 2. Función de limpieza de datos con protección
def limpiar_datos_ptar(df):
    if df is None or df.empty: return pd.DataFrame()
    df.columns = df.columns.str.strip()
    mapeo = {
        'ph': 'ph', 'pH': 'ph', 'temp': 'temp', 'Temperatura': 'temp',
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
    return df

# 3. Conexión y Carga
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_raw = conn.read(ttl=0)
    df_base = limpiar_datos_ptar(df_raw)

    # --- BARRA LATERAL (ORIGINAL) ---
    try:
        st.sidebar.image("logo-white-kenzo.png", use_container_width=True)
    except:
        pass
    
    st.sidebar.header("Filtros de Análisis")
    busqueda_q = st.sidebar.text_input("🔍 Buscar Químico:", "")

    if not df_base.empty and 'fecha' in df_base.columns:
        df_base = df_base.dropna(subset=['fecha'])
        min_f, max_f = min(df_base['fecha']), max(df_base['fecha'])
        rango_fechas = st.sidebar.date_input("Rango de fechas:", [min_f, max_f])
        if len(rango_fechas) == 2:
            df_base = df_base[(df_base['fecha'] >= rango_fechas[0]) & (df_base['fecha'] <= rango_fechas[1])]

    if not df_base.empty and 'proceso' in df_base.columns:
        lista_p = sorted(df_base['proceso'].dropna().unique().tolist())
        procesos_sel = st.sidebar.multiselect("Procesos:", lista_p, default=lista_p)
        df_filtrado = df_base[df_base['proceso'].isin(procesos_sel)]
    else:
        df_filtrado = df_base

    if busqueda_q and not df_filtrado.empty and 'quimicos' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['quimicos'].astype(str).str.contains(busqueda_q, case=False, na=False)]

    # --- CUERPO PRINCIPAL ---
    t1, t2, t3 = st.tabs(["📊 Dashboard Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with t1:
        if not df_filtrado.empty:
            m1, m2, m3 = st.columns(3)
            m1.metric("Promedio pH", f"{df_filtrado['ph'].mean():.2f}" if 'ph' in df_filtrado.columns else "N/A")
            m2.metric("Temp Promedio", f"{df_filtrado['temp'].mean():.1f} °C" if 'temp' in df_filtrado.columns else "N/A")
            m3.metric("Registros", len(df_filtrado))
            st.plotly_chart(px.line(df_filtrado.sort_values('fecha'), x='fecha', y='ph', title="Histórico pH"), use_container_width=True)
            st.dataframe(df_filtrado, use_container_width=True)

    with t3:
        st.subheader("🛠️ Plano Interactivo de Mantenimiento")
        st.info("Haz clic en los puntos de colores para ver el historial.")

        # Datos del plano lateral de la PTAR
        equipos_data = {
            'Equipo': ['Homogeneización', 'Coagulación', 'Sedimentador', 'Oxidación', 'Filtración', 'Agua Tratada', 'Bomba B1', 'Bomba B2'],
            'X': [10, 25, 45, 65, 80, 95, 53, 63],
            'Y': [50, 40, 60, 50, 50, 40, 30, 30],
            'Estado': ['Al día', 'Próximo', 'Al día', 'Al día', 'Vencido', 'Al día', 'Al día', 'Próximo']
        }
        df_eq = pd.DataFrame(equipos_data)
        
        # Gráfico Scatter con puntos brillantes para evitar el "cuadro negro"
        fig_p = px.scatter(df_eq, x='X', y='Y', text='Equipo', color='Estado',
                           color_discrete_map={'Al día': '#00FF00', 'Próximo': '#FFFF00', 'Vencido': '#FF0000'},
                           range_x=[0, 100], range_y=[0, 100])
        
        fig_p.update_traces(marker=dict(size=35, line=dict(width=2, color='white'), opacity=0.8),
                            textposition='top center', textfont=dict(color='white', size=12))
        
        fig_p.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(40,40,40,1)', # Fondo gris para contraste
                            xaxis=dict(visible=False), yaxis=dict(visible=False), height=550)

        # Captura de clic
        clic = plotly_events(fig_p, click_event=True, override_height=550)

        if clic:
            idx = clic[0]['pointIndex']
            st.success(f"### 📑 Historial: {df_eq.iloc[idx]['Equipo']}")
            st.table(pd.DataFrame([{"Fecha": "2026-04-06", "Tarea": "Revisión preventiva", "Estado": "OK"}]))

except Exception as e:
    st.error(f"Error: {e}")
