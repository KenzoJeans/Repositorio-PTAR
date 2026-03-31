import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

import streamlit as st
import pandas as pd
import plotly.express as px

# CONFIGURACIÓN
st.set_page_config(page_title="PTAR Real-Time", layout="wide")
st.title("💧 Control de Vertimientos (Tiempo Real)")

# --- CONEXIÓN CON GOOGLE SHEETS ---
# REEMPLAZA EL ENLACE DE ABAJO POR EL TUYO:
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Wjlr5uC4YMBIQlTXPOcdXThFff1tks5jmLYcr5k5IPc/edit?usp=sharing"

@st.cache_data(ttl=600) # Se actualiza cada 10 minutos automáticamente
def cargar_desde_sheets(url):
    # Truco para convertir el link de edición en link de descarga CSV
    csv_url = url.replace('/edit#gid=', '/export?format=csv&gid=')
    df = pd.read_csv(csv_url)
    
    # Limpieza de nombres (Basado en tu imagen)
    df = df.rename(columns={
        'Fecha del reporte:': 'Fecha',
        'Proceso a reportar:': 'Proceso',
        'pH (Use valores con coma para los decimales):': 'pH',
        'Temperatura °C (Use valores con coma para los decimales):': 'Temp',
        'Sólidos suspendidos mg/L (Use valores con coma para los decimales):': 'Solidos'
    })
    
    # Convertir pH y otros a números (por si vienen con comas de Google)
    # Reemplazamos coma por punto para que Python los entienda
    for col in ['pH', 'Temp', 'Solidos']:
        if df[col].dtype == object:
            df[col] = df[col].str.replace(',', '.').astype(float)
            
    df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True)
    return df

# Ejecutar carga
try:
    df = cargar_desde_sheets(SHEET_URL)
    st.success("✅ Datos sincronizados con Google Sheets")
except Exception as e:
    st.error(f"Error al conectar: {e}")
    st.stop()

# --- EL RESTO DEL DASHBOARD (Filtros y Gráficos) ---
st.sidebar.header("Filtros")
procesos = st.sidebar.multiselect("Filtrar Procesos:", options=df['Proceso'].unique(), default=df['Proceso'].unique())
df_filt = df[df['Proceso'].isin(procesos)]

col1, col2, col3 = st.columns(3)
col1.metric("pH Promedio", f"{df_filt['pH'].mean():.2f}")
col2.metric("Temperatura Prom.", f"{df_filt['Temp'].mean():.1f} °C")
col3.metric("Sólidos Prom.", f"{df_filt['Solidos'].mean():.1f}")

st.plotly_chart(px.line(df_filt, x='Fecha', y='pH', color='Proceso', markers=True, title="Tendencia de pH"), use_container_width=True)
