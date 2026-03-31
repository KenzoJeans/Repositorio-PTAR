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
    @st.cache_data(ttl=600)
def cargar_desde_sheets(url):
    csv_url = url.replace('/edit#gid=', '/export?format=csv&gid=')
    df = pd.read_csv(csv_url)
    
    # --- PASO DE SEGURIDAD ---
    # Esto elimina espacios en blanco al principio y final de cada nombre de columna
    df.columns = [c.strip() for c in df.columns]
    
    # Vamos a usar una técnica más segura: buscar palabras clave en lugar de la frase exacta
    nuevos_nombres = {}
    for col in df.columns:
        if 'Fecha' in col: nuevos_nombres[col] = 'Fecha'
        elif 'Proceso' in col: nuevos_nombres[col] = 'Proceso'
        elif 'pH' in col: nuevos_nombres[col] = 'pH'
        elif 'Temperatura' in col: nuevos_nombres[col] = 'Temp'
        elif 'Sólidos' in col or 'Sólidos' in col: nuevos_nombres[col] = 'Solidos'
    
    df = df.rename(columns=nuevos_nombres)
    
    # Verificar que las columnas clave existan ahora
    columnas_necesarias = ['pH', 'Temp', 'Solidos', 'Fecha', 'Proceso']
    for col in columnas_necesarias:
        if col not in df.columns:
            # Si aún falla, esto nos dirá qué columnas SÍ detectó para poder corregir
            st.error(f"No encontré la columna '{col}'. Las columnas detectadas son: {list(df.columns)}")
            st.stop()

    # Limpieza de datos (Comas a Puntos)
    for col in ['pH', 'Temp', 'Solidos']:
        df[col] = df[col].astype(str).str.replace(',', '.').astype(float)
            
    df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True)
    return df

# --- EL RESTO DEL DASHBOARD (Filtros y Gráficos) ---
st.sidebar.header("Filtros")
procesos = st.sidebar.multiselect("Filtrar Procesos:", options=df['Proceso'].unique(), default=df['Proceso'].unique())
df_filt = df[df['Proceso'].isin(procesos)]

col1, col2, col3 = st.columns(3)
col1.metric("pH Promedio", f"{df_filt['pH'].mean():.2f}")
col2.metric("Temperatura Prom.", f"{df_filt['Temp'].mean():.1f} °C")
col3.metric("Sólidos Prom.", f"{df_filt['Solidos'].mean():.1f}")

st.plotly_chart(px.line(df_filt, x='Fecha', y='pH', color='Proceso', markers=True, title="Tendencia de pH"), use_container_width=True)
