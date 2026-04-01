import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Configuración de la página
st.set_page_config(page_title="Dashboard PTAR", layout="wide", page_icon="💧")

st.title("📊 Monitor de Parámetros de vertimiento en Planta de tratamiento - Kenzo Jeans SAS")
st.markdown("---")

# 2. Función de limpieza y normalización de datos
def preparar_datos(df):
    # Limpieza de espacios en los nombres de las columnas
    df.columns = df.columns.str.strip()
    
    # Mapeo según tu captura de pantalla
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

    # --- SOLUCIÓN AL ERROR DE 'STRING DTYPE' ---
    # Convertimos las columnas críticas a números, manejando comas y textos
    cols_numericas = ['ph', 'temp', 'sst', 'caudal']
    for col in cols_numericas:
        if col in df.columns:
            # Convertimos a string, reemplazamos coma por punto y luego a número
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    # Convertir fecha a formato datetime
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha']).dt.date
    
    # Eliminamos filas que no tengan pH (asumiendo que es el dato principal)
    df = df.dropna(subset=['ph'])
    
    return df

# 3. Conexión y ejecución
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_raw = conn.read()
    
    df = preparar_datos(df_raw)

    # --- INTERFAZ DEL DASHBOARD ---
    
    # Sidebar con filtros
    st.sidebar.header("Filtros de Planta")
    if "proceso" in df.columns:
        proceso_sel = st.sidebar.multiselect(
            "Selecciona el Proceso:",
            options=df["proceso"].unique(),
            default=df["proceso"].unique()
        )
        df_filtrado = df[df["proceso"].isin(proceso_sel)]
    else:
        df_filtrado = df

    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Promedio pH", f"{df_filtrado['ph'].mean():.2f}")
    with col2:
        st.metric("Temp Promedio", f"{df_filtrado['temp'].mean():.1f} °C")
    with col3:
        st.metric("SST Promedio", f"{df_filtrado['sst'].mean():.2f}")
    with col4:
        st.metric("Registros", len(df_filtrado))

    # Gráficos
    st.markdown("### Tendencias en el tiempo")
    tab1, tab2 = st.tabs(["Línea de Tiempo pH", "Tabla de Datos"])
    
    with tab1:
        # Gráfico de pH por fecha
        chart_data = df_filtrado.groupby('fecha')['ph'].mean()
        st.line_chart(chart_data)
        
    with tab2:
        st.dataframe(df_filtrado, use_container_width=True)

except Exception as e:
    st.error(f"Se presentó un detalle técnico: {e}")
    st.info("💡 Tip: Revisa que las columnas en Google Sheets no hayan cambiado de nombre.")
