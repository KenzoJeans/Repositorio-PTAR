import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Configuración de la página (Layout ancho para mejores gráficas)
st.set_page_config(page_title="Dashboard PTAR Pro", layout="wide", page_icon="💧")

# Estilo personalizado para el título
st.markdown("""
    <style>
    .main-title { font-size:36px !important; font-weight: bold; color: #1E88E5; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<p class="main-title">🌊 Sistema de Control de Vertimientos - PTAR</p>', unsafe_allow_html=True)
st.markdown("---")

# 2. Función de procesamiento de datos (El "Motor" del Dashboard)
def preparar_datos(df):
    # Limpieza de nombres de columnas
    df.columns = df.columns.str.strip()
    
    # Mapeo de columnas basado en tu formulario
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

    # Conversión estricta a números (Manejo de comas y errores)
    cols_numericas = ['ph', 'temp', 'sst', 'caudal']
    for col in cols_numericas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    # Manejo de fechas
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha']).dt.date
    
    # Limpieza: quitamos filas sin pH que es nuestro dato clave
    df = df.dropna(subset=['ph'])
    
    return df

# 3. Conexión y Lógica Principal
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_raw = conn.read()
    df = preparar_datos(df_raw)

    # --- SIDEBAR: FILTROS ---
    st.sidebar.header("🔍 Panel de Filtros")
    
    # Filtro por Proceso
    lista_procesos = df["proceso"].unique().tolist()
    proceso_sel = st.sidebar.multiselect("Filtrar por Proceso:", options=lista_procesos, default=lista_procesos)
    
    # Filtro por Rango de Fechas
    fecha_min, fecha_max = df["fecha"].min(), df["fecha"].max()
    rango_fecha = st.sidebar.date_input("Rango de Fechas:", [fecha_min, fecha_max], min_value=fecha_min, max_value=fecha_max)

    # Aplicar filtros
    df_filtrado = df[df["proceso"].isin(proceso_sel)]
    if len(rango_fecha) == 2:
        df_filtrado = df_filtrado[(df_filtrado["fecha"] >= rango_fecha[0]) & (df_filtrado["fecha"] <= rango_fecha[1])]

    # --- SECCIÓN 1: MÉTRICAS CLAVE ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Promedio pH", f"{df_filtrado['ph'].mean():.2f}")
    with col2:
        st.metric("Temp Promedio", f"{df_filtrado['temp'].mean():.1f} °C")
    with col3:
        st.metric("SST Promedio", f"{df_filtrado['sst'].mean():.2f}")
    with col4:
        st.metric("N° Reportes", len(df_filtrado))

    # --- SECCIÓN 2: ALERTAS ---
    st.markdown("### ⚠️ Estado de Cumplimiento")
    # Ejemplo de límites: pH (6.0 - 9.0) y Temp (máx 40°C)
    alertas_ph = df_filtrado[(df_filtrado['ph'] < 6) | (df_filtrado['ph'] > 9)]
    alertas_temp = df_filtrado[df_filtrado['temp'] > 40]

    if not alertas_ph.empty or not alertas_temp.empty:
        st.error(f"Se detectaron {len(alertas_ph) + len(alertas_temp)} registros fuera de la norma operativa.")
    else:
        st.success("✅ Todos los parámetros están dentro de los rangos normales.")

    # --- SECCIÓN 3: GRÁFICAS AVANZADAS ---
    st.markdown("---")
    col_izq, col_der = st.columns(2)

    with col_izq:
        st.subheader("📈 Tendencia de pH")
        chart_ph = df_filtrado.groupby('fecha')['ph'].mean()
        st.line_chart(chart_ph)
        
        st.subheader("🧪 Sólidos (SST) por Proceso")
        # Gráfica de barras pedida: Proceso vs Sólidos
