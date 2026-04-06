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

    # --- BARRA LATERAL (LOGO Y FILTROS) ---
    try:
        st.sidebar.image("logo-white-kenzo.png", use_container_width=True)
    except:
        st.sidebar.markdown("### 👖 KENZO JEANS PTAR")

    st.sidebar.header("Filtros de Análisis")
    
    # Filtro de Fecha
    if not df_base.empty and 'fecha' in df_base.columns:
        min_f, max_f = min(df_base['fecha']), max(df_base['fecha'])
        rango_fechas = st.sidebar.date_input("Rango de fechas:", [min_f, max_f])
        if len(rango_fechas) == 2:
            df_base = df_base[(df_base['fecha'] >= rango_fechas[0]) & (df_base['fecha'] <= rango_fechas[1])]

    # Filtro de Proceso
    if not df_base.empty and 'proceso' in df_base.columns:
        lista_p = sorted(df_base['proceso'].unique().tolist())
        procesos_sel = st.sidebar.multiselect("Selecciona el Proceso:", lista_p, default=lista_p)
        df_filtrado = df_base[df_base['proceso'].isin(procesos_sel)]
    else:
        df_filtrado = df_base

    # --- FILTRO DE BÚSQUEDA POR TEXTO (QUÍMICOS) ---
    if not df_filtrado.empty and 'quimicos' in df_filtrado.columns:
        busqueda_q = st.sidebar.text_input("🔍 Buscar Químico:", "")
        if busqueda_q:
            df_filtrado = df_filtrado[df_filtrado['quimicos'].astype(str).str.contains(busqueda_q, case=False, na=False)]

    # --- CUERPO PRINCIPAL ---
    t1, t2, t3 = st.tabs(["📊 Dashboard Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with t1:
        if not df_filtrado.empty:
            # MÉTRICAS SUPERIORES
            m1, m2, m3, m4 = st.columns(4)
            avg_ph = df_filtrado['ph'].mean()
            avg_temp = df_filtrado['temp'].mean()
            avg_sst = df_filtrado['sst'].mean()

            m1.metric("Promedio pH", f"{avg_ph:.2f}", delta="EN NORMA" if 6<=avg_ph<=9 else "ALERTA", delta_color="normal" if 6<=avg_ph<=9 else "inverse")
            m2.metric("Temp Promedio", f"{avg_temp:.1f} °C")
            m3.metric("SST Promedio", f"{avg_sst:.2f} mg/L")
            m4.metric("Registros", len(df_filtrado))

            # FILA 1: GRÁFICA DE PH (HISTÓRICO)
            st.subheader("📈 Evolución Histórica de pH")
            fig_ph = px.line(df_filtrado.sort_values('fecha'), x='fecha', y='ph', color='proceso', markers=True, title="pH por Fecha y Proceso")
            fig_ph.add_hline(y=9.0, line_dash="dash", line_color="red", annotation_text="Límite Max")
            fig_ph.add_hline(y=6.0, line_dash="dash", line_color="red", annotation_text="Límite Min")
            st.plotly_chart(fig_ph, use_container_width=True)

            # FILA 2: SST Y TEMPERATURA
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 Sólidos Suspendidos (SST)")
                df_sst_avg = df_filtrado.groupby('proceso')['sst'].mean().reset_index()
                fig_sst = px.bar(df_sst_avg, x='proceso', y='sst', color='sst', color_continuous_scale='Viridis', title="Promedio SST por Proceso")
                st.plotly_chart(fig_sst, use_container_width=True)

            with col2:
                st.subheader("🌡️ Temperatura por Etapa")
                fig_temp = px.box(df_filtrado, x='proceso', y='temp', color='proceso', title="Dispersión de Temperatura")
                st.plotly_chart(fig_temp, use_container_width=True)

            # FILA 3: TABLA DE DATOS
            st.subheader("📋 Detalle de Datos Filtrados")
            st.dataframe(df_filtrado, use_container_width=True)
            
        else:
            st.warning("No hay datos para mostrar con los filtros actuales.")

    with t2: st.info("Módulo de Agua Tratada en construcción.")
    with t3: st.info("Módulo de Mantenimiento en construcción.")

except Exception as e:
    st.error(f"Error en la aplicación: {e}")
