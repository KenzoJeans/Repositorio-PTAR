import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Control PTAR", layout="wide")
st.title("💧 Control de Vertimientos")

# Reemplaza con tu link público de Google Sheets
SHEET_URL = "https://docs.google.com/spreadsheets/d/TU_ID_AQUÍ/edit#gid=0"

@st.cache_data(ttl=60) 
def cargar_datos(url):
    csv_url = url.replace('/edit#gid=', '/export?format=csv&gid=')
    # Ya no necesitamos encoding complejo porque el archivo está limpio
    df = pd.read_csv(csv_url)
    
    # Aseguramos que los números sean números (por si hay comas)
    for col in ['pH', 'Temp', 'Solidos']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    # Convertimos la fecha
    if 'Fecha' in df.columns:
        df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True)
    return df

# 2. EJECUCIÓN
try:
    df = cargar_datos(SHEET_URL)
    
    # Filtros rápidos
    proceso = st.sidebar.multiselect("Proceso:", df['Proceso'].unique(), default=df['Proceso'].unique())
    df_filt = df[df['Proceso'].isin(proceso)]

    # Métricas
    c1, c2, c3 = st.columns(3)
    c1.metric("pH Promedio", f"{df_filt['pH'].mean():.2f}")
    c2.metric("Temp Promedio", f"{df_filt['Temp'].mean():.1f} °C")
    c3.metric("Sólidos Promedio", f"{df_filt['Solidos'].mean():.1f}")

    # Gráfico
    fig = px.line(df_filt, x='Fecha', y='pH', color='Proceso', markers=True, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Error: {e}")
