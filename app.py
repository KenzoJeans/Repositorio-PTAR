import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 1. Configuración de página y estilo
st.set_page_config(page_title="Sistema Control PTAR", layout="wide", page_icon="💧")
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)

st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# 2. Función de limpieza y normalización de datos
def limpiar_datos_ptar(df):
    if df is None or df.empty: return pd.DataFrame()
    df.columns = df.columns.str.strip()
    
    # Mapeo de columnas detectadas en tu Sheet
    mapeo = {
        'ph': 'ph', 'pH': 'ph', 'PH': 'ph',
        'temp': 'temp', 'Temperatura': 'temp',
        'sst': 'sst', 'Solidos suspendidos': 'sst',
        'Fecha del reporte': 'fecha', 'fecha': 'fecha',
        'Proceso a reportar': 'proceso'
    }
    df = df.rename(columns={k: v for k, v in mapeo.items() if k in df.columns})

    # Conversión numérica y de fecha
    for col in ['ph', 'temp', 'sst']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce').dt.date
    
    return df.dropna(subset=['ph'])

# 3. Conexión y Carga
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Usamos la carga por defecto que es la más estable para tu cuenta
    df_raw = conn.read(ttl=0)
    df = limpiar_datos_ptar(df_raw)

    # --- BARRA LATERAL (FILTROS) ---
    st.sidebar.header("Filtros de Análisis")
    if 'proceso' in df.columns:
        lista_procesos = df['proceso'].unique().tolist()
        procesos_sel = st.sidebar.multiselect("Selecciona el Proceso:", lista_procesos, default=lista_procesos)
        df_filtrado = df[df['proceso'].isin(procesos_sel)]
    else:
        df_filtrado = df

    # --- CUERPO PRINCIPAL (PESTAÑAS) ---
    t1, t2, t3 = st.tabs(["📊 Dashboard Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with t1:
        if not df_filtrado.empty:
            # MÉTRICAS CLAVE
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Promedio pH", f"{df_filtrado['ph'].mean():.2f}")
            m2.metric("Temp Promedio", f"{df_filtrado['temp'].mean():.1f} °C")
            m3.metric("SST Promedio", f"{df_filtrado['sst'].mean():.2f}")
            m4.metric("Total Registros", len(df_filtrado))

            # GRÁFICAS PRO
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.subheader("📈 Tendencia de pH")
                fig_ph = px.line(df_filtrado.sort_values('fecha'), x='fecha', y='ph', 
                               markers=True, color_discrete_sequence=['#1E88E5'])
                fig_ph.add_hline(y=9.0, line_dash="dash", line_color="red", annotation_text="Límite Máx")
                fig_ph.add_hline(y=6.0, line_dash="dash", line_color="red", annotation_text="Límite Mín")
                st.plotly_chart(fig_ph, use_container_width=True)

            with col_g2:
                st.subheader("📊 Sólidos (SST) por Proceso")
                fig_sst = px.bar(df_filtrado, x='proceso', y='sst', color='proceso',
                                title="Distribución de Sólidos")
                st.plotly_chart(fig_sst, use_container_width=True)

            st.subheader("📋 Detalle de Datos Filtrados")
            st.dataframe(df_filtrado, use_container_width=True)
        else:
            st.warning("Selecciona al menos un proceso en la barra lateral para ver los datos.")

    with t2:
        st.info("Módulo de Agua Tratada: Conexión establecida con la base de datos maestra.")

    with t3:
        st.info("Módulo de Mantenimiento: Listo para recibir registros de equipos.")

except Exception as e:
    st.error(f"Error de sistema: {e}")
