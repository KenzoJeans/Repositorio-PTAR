import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 1. Configuración de página
st.set_page_config(page_title="Sistema Control PTAR", layout="wide", page_icon="💧")
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)
st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# 2. Función de limpieza de datos
def limpiar_datos_ptar(df):
    if df is None or df.empty: return pd.DataFrame()
    df.columns = df.columns.str.strip()
    
    mapeo = {
        'ph': 'ph', 'pH': 'ph', 'PH': 'ph',
        'temp': 'temp', 'Temperatura': 'temp',
        'sst': 'sst', 'Solidos suspendidos': 'sst',
        'Fecha del reporte': 'fecha', 'fecha': 'fecha',
        'Proceso a reportar': 'proceso'
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
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_raw = conn.read(ttl=0)
    df = limpiar_datos_ptar(df_raw)

    # --- BARRA LATERAL (FILTROS) ---
    st.sidebar.header("Filtros de Análisis")
    if 'proceso' in df.columns:
        lista_procesos = sorted(df['proceso'].unique().tolist())
        procesos_sel = st.sidebar.multiselect("Selecciona el Proceso:", lista_procesos, default=lista_procesos)
        df_filtrado = df[df['proceso'].isin(procesos_sel)]
    else:
        df_filtrado = df

    # --- CUERPO PRINCIPAL ---
    t1, t2, t3 = st.tabs(["📊 Dashboard Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with t1:
        if not df_filtrado.empty:
            # MÉTRICAS SUPERIORES
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Promedio pH", f"{df_filtrado['ph'].mean():.2f}")
            m2.metric("Temp Promedio", f"{df_filtrado['temp'].mean():.1f} °C")
            m3.metric("SST Promedio", f"{df_filtrado['sst'].mean():.2f}")
            m4.metric("Total Registros", len(df_filtrado))

            # --- SECCIÓN DE PH ---
            st.subheader("📈 Análisis de pH")
            
            # 1. Evolución de pH en el tiempo
            fig_tiempo = px.line(df_filtrado.sort_values('fecha'), x='fecha', y='ph', 
                               markers=True, title="Evolución del pH en el tiempo")
            fig_tiempo.add_hline(y=9.0, line_dash="dash", line_color="red", annotation_text="Límite Máx")
            fig_tiempo.add_hline(y=6.0, line_dash="dash", line_color="red", annotation_text="Límite Mín")
            st.plotly_chart(fig_tiempo, use_container_width=True)

            # 2. Promedio de pH por Proceso (Gráfica de líneas)
            df_proc = df_filtrado.groupby('proceso')['ph'].mean().reset_index()
            fig_proc = px.line(df_proc, x='proceso', y='ph', markers=True,
                             title="Promedio de pH por Proceso",
                             color_discrete_sequence=['#43A047'])
            st.plotly_chart(fig_proc, use_container_width=True)

            # --- SECCIÓN DE SÓLIDOS ---
            st.subheader("📊 Análisis de Sólidos (SST)")
            df_sst_proc = df_filtrado.groupby('proceso')['sst'].mean().reset_index()
            fig_sst = px.bar(df_sst_proc, x='proceso', y='sst', 
                            color='proceso', title="Promedio de Sólidos (SST) por Proceso")
            st.plotly_chart(fig_sst, use_container_width=True)

            st.subheader("📋 Detalle de Datos")
            st.dataframe(df_filtrado, use_container_width=True)
        else:
            st.warning("Selecciona al menos un proceso en la barra lateral.")

    with t2:
        st.info("Módulo de Agua Tratada configurado.")

    with t3:
        st.info("Módulo de Mantenimiento configurado.")

except Exception as e:
    st.error(f"Error en la ejecución: {e}")
