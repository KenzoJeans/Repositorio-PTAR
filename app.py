import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 1. Configuración de página
st.set_page_config(page_title="Sistema Control PTAR", layout="wide", page_icon="💧")
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)
st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;"> SGA - Planta de Tratamiento</p>', unsafe_allow_html=True)

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
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_raw = conn.read(ttl=0)
    df_base = limpiar_datos_ptar(df_raw)

    # --- BARRA LATERAL (FILTROS) ---
    # Puedes usar una URL directa a la imagen o la ruta de un archivo local
logo_url = "https://kenzojeans.com.co/" 

st.sidebar.image(logo_url, use_container_width=True)
st.sidebar.header("Filtros de Análisis")
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

    # --- CUERPO PRINCIPAL ---
    t1, t2, t3 = st.tabs(["📊 Dashboard Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with t1:
        if not df_filtrado.empty:
            # --- MÉTRICAS CON SEMÁFORO ---
            m1, m2, m3, m4 = st.columns(4)
            
            avg_ph = df_filtrado['ph'].mean()
            avg_temp = df_filtrado['temp'].mean()
            avg_sst = df_filtrado['sst'].mean()

            # Semáforo pH (Norma: 6.0 - 9.0)
            status_ph = "normal" if 6.0 <= avg_ph <= 9.0 else "inverse"
            m1.metric("Promedio pH", f"{avg_ph:.2f}", 
                      delta="DENTRO DE RANGO" if status_ph == "normal" else "FUERA DE RANGO",
                      delta_color=status_ph)

            # Semáforo Temperatura (Límite: 40°C)
            status_temp = "normal" if avg_temp <= 40 else "inverse"
            m2.metric("Temp Promedio", f"{avg_temp:.1f} °C",
                      delta="ESTABLE" if status_temp == "normal" else "ELEVADA",
                      delta_color=status_temp)

            # Semáforo SST (Límite: 50)
            status_sst = "normal" if avg_sst <= 50 else "inverse"
            m3.metric("SST Promedio", f"{avg_sst:.2f}",
                      delta="ÓPTIMO" if status_sst == "normal" else "REVISAR",
                      delta_color=status_sst)

            m4.metric("Total Registros", len(df_filtrado))

            # --- GRÁFICAS ---
            st.subheader("📈 Análisis de pH")
            fig_t = px.line(df_filtrado.sort_values('fecha'), x='fecha', y='ph', markers=True, title="Evolución Histórica de pH")
            fig_t.add_hline(y=9.0, line_dash="dash", line_color="red")
            fig_t.add_hline(y=6.0, line_dash="dash", line_color="red")
            st.plotly_chart(fig_t, use_container_width=True)

            # Semáforo de pH por Proceso
            df_p = df_filtrado.groupby('proceso')['ph'].mean().reset_index()
            fig_p = px.scatter(df_p, x='proceso', y='ph', color='ph', 
                             color_continuous_scale='RdYlGn_r', range_color=[5, 10], size=[15]*len(df_p),
                             title="Promedio de pH por Proceso")
            fig_p.update_traces(mode='lines+markers', line_color='lightgrey')
            st.plotly_chart(fig_p, use_container_width=True)

            # SST y Temperatura
            col_sst, col_temp = st.columns(2)
            with col_sst:
                st.subheader("📊 Sólidos (SST)")
                df_s = df_filtrado.groupby('proceso')['sst'].mean().reset_index()
                fig_s = px.bar(df_s, x='proceso', y='sst', color='sst', title="Promedio SST por Etapa")
                st.plotly_chart(fig_s, use_container_width=True)

            with col_temp:
                st.subheader("🌡️ Temperatura")
                df_temp_plot = df_filtrado.groupby('proceso')['temp'].mean().reset_index()
                fig_temp = px.line(df_temp_plot, x='proceso', y='temp', markers=True, title="Temperatura por Etapa")
                st.plotly_chart(fig_temp, use_container_width=True)

            st.subheader("📋 Detalle de Datos")
            st.dataframe(df_filtrado, use_container_width=True)
        else:
            st.warning("No hay datos para mostrar con los filtros actuales.")

    with t2: st.info("Módulo de Agua Tratada.")
    with t3: st.info("Módulo de Mantenimiento.")

except Exception as e:
    st.error(f"Se detectó un error en la aplicación: {e}")
