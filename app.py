import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Configuración de la página
st.set_page_config(page_title="Dashboard PTAR Pro", layout="wide", page_icon="💧")

# Estilo personalizado
st.markdown("""
    <style>
    .main-title { font-size:36px !important; font-weight: bold; color: #1E88E5; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<p class="main-title">🌊 Sistema de Control de Vertimientos - PTAR</p>', unsafe_allow_html=True)
st.markdown("---")

# 2. Función de procesamiento de datos
def preparar_datos(df):
    df.columns = df.columns.str.strip()
    
    mapeo = {
        'Marca temporal': 'timestamp',
        'Fecha del reporte': 'fecha',
        'Hora del reporte': 'hora',
        'Proceso a reportar': 'proceso',
        'ph': 'ph',
        'Temperatura': 'temp',
        'Solidos suspendidos': 'sst',
        'Productos quimicos utilizados en el proceso': 'quimicos',
        'Caracteristicas visuales del vertimiento': 'visuales',
        'Caudal del vertimiento': 'caudal',
        'Suba aqui evidencia de la muestra tomada y e': 'evidencia'
    }
    
    df = df.rename(columns=mapeo)

    cols_numericas = ['ph', 'temp', 'sst', 'caudal']
    for col in cols_numericas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha']).dt.date
    
    df = df.dropna(subset=['ph'])
    return df

# 3. Conexión y Lógica Principal
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_raw = conn.read()
    df = preparar_datos(df_raw)

    # --- SIDEBAR ---
    st.sidebar.header("🔍 Panel de Filtros")
    lista_procesos = df["proceso"].unique().tolist()
    proceso_sel = st.sidebar.multiselect("Filtrar por Proceso:", options=lista_procesos, default=lista_procesos)
    
    fecha_min, fecha_max = df["fecha"].min(), df["fecha"].max()
    rango_fecha = st.sidebar.date_input("Rango de Fechas:", [fecha_min, fecha_max])

    df_filtrado = df[df["proceso"].isin(proceso_sel)]
    if len(rango_fecha) == 2:
        df_filtrado = df_filtrado[(df_filtrado["fecha"] >= rango_fecha[0]) & (df_filtrado["fecha"] <= rango_fecha[1])]

    # --- MÉTRICAS PRINCIPALES ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Promedio pH", f"{df_filtrado['ph'].mean():.2f}")
    with col2:
        st.metric("Temp Promedio", f"{df_filtrado['temp'].mean():.1f} °C")
    with col3:
        st.metric("SST Promedio", f"{df_filtrado['sst'].mean():.2f}")
    with col4:
        st.metric("Total Registros", len(df_filtrado))

    # --- NUEVA SECCIÓN: CONTADOR POR PROCESO ---
    st.markdown("### 📊 Cantidad de Registros por Proceso")
    
    # Creamos el conteo
    conteo_procesos = df_filtrado['proceso'].value_counts()
    
    # Mostramos los conteos en columnas pequeñas para que se vea ordenado
    columnas_conteo = st.columns(len(conteo_procesos))
    for i, (proc, cant) in enumerate(conteo_procesos.items()):
        with columnas_conteo[i]:
            st.info(f"**{proc}** \n\n {cant} registros")

    # --- ALERTAS ---
    st.markdown("### ⚠️ Estado de Cumplimiento")
    alertas_ph = df_filtrado[(df_filtrado['ph'] < 6) | (df_filtrado['ph'] > 9)]
    alertas_temp = df_filtrado[df_filtrado['temp'] > 40]

    if not alertas_ph.empty or not alertas_temp.empty:
        st.error(f"Atención: {len(alertas_ph) + len(alertas_temp)} registros fuera de norma.")
    else:
        st.success("✅ Parámetros dentro de los rangos normales.")

    # --- GRÁFICAS ---
    st.markdown("---")
    col_izq, col_der = st.columns(2)

    with col_izq:
        st.subheader("📈 Tendencia de pH")
        chart_ph = df_filtrado.groupby('fecha')['ph'].mean()
        st.line_chart(chart_ph)
        
        st.subheader("🧪 Sólidos (SST) por Proceso")
        sst_data = df_filtrado.groupby('proceso')['sst'].mean().sort_values()
        st.bar_chart(sst_data)

    with col_der:
        st.subheader("🌡️ Temperatura vs pH")
        st.scatter_chart(data=df_filtrado, x='temp', y='ph', color='proceso')
        
        st.subheader("📋 Detalle de Datos")
        st.dataframe(df_filtrado[['fecha', 'proceso', 'ph', 'temp', 'sst']], use_container_width=True)

except Exception as e:
    st.error(f"Error en el procesamiento: {e}")
    st.info("Revisa la conexión a Google Sheets y los Secrets.")
