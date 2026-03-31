import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Control PTAR", layout="wide")
st.title("💧 Control de Vertimientos")

# 1. ENLACE (Asegúrate de que este sea tu link actual)
SHEET_URL = "https://docs.google.com/spreadsheets/d/TU_ID_AQUÍ/edit#gid=0"

@st.cache_data(ttl=10) # Bajamos el tiempo a 10 segundos para pruebas
def cargar_datos(url):
    # Transformación del link a formato descarga
    csv_url = url.replace('/edit#gid=', '/export?format=csv&gid=')
    # Ya no debería fallar el encoding porque limpiaste el archivo
    df = pd.read_csv(csv_url)
    
    # Limpieza de datos por si acaso quedaron comas
    for col in ['pH', 'Temp', 'Solidos']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    if 'Fecha' in df.columns:
        df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True)
    return df

# 2. EJECUCIÓN
try:
    df = cargar_datos(SHEET_URL)
    st.success("✅ Datos sincronizados con el Sheet limpio")

    # Mostrar la tabla para confirmar que ya no hay caracteres raros
    st.write("### Vista de datos limpios", df.head())

    # Gráfico simple de pH
    if 'pH' in df.columns and 'Fecha' in df.columns:
        fig = px.line(df, x='Fecha', y='pH', color='Proceso', markers=True)
        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Error detectado: {e}")
