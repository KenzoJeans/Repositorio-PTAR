import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Control PTAR", layout="wide")
st.title("💧 Control de Vertimientos")

# 1. ENLACE - Asegúrate de que termine en #gid=0 o el número de tu hoja
SHEET_URL = "https://docs.google.com/spreadsheets/d/TU_ID_AQUÍ/edit#gid=0"

@st.cache_data(ttl=10)
def cargar_datos(url):
    # Transformación del link
    csv_url = url.replace('/edit#gid=', '/export?format=csv&gid=')
    
    # EL CAMBIO CLAVE: 'latin-1' es más robusto para archivos con tildes de Excel/Sheets
    # encoding_errors='ignore' hará que si hay un carácter que no entiende, simplemente lo salte
    df = pd.read_csv(csv_url, encoding='latin-1', encoding_errors='ignore')
    
    # Limpiar espacios en blanco en los nombres de columnas
    df.columns = [c.strip() for c in df.columns]
    
    # Convertir números (manejando comas decimales)
    # Basado en tus nuevos nombres: 'ph', 'Temperatura', 'Solidos suspendidos'
    for col in ['ph', 'Temperatura', 'Solidos suspendidos']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    if 'Fecha' in df.columns:
        df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
    
    return df

# 2. EJECUCIÓN
try:
    df = cargar_datos(SHEET_URL)
    
    # Mensaje de éxito que te muestra qué columnas leyó
    st.success(f"✅ Datos cargados. Columnas: {', '.join(df.columns)}")

    # Filtros y Gráfico
    if 'ph' in df.columns and 'Fecha' in df.columns:
        fig = px.line(df, x='Fecha', y='ph', color='Proceso' if 'Proceso' in df.columns else None,
                     markers=True, title="Histórico de pH")
        st.plotly_chart(fig, use_container_width=True)
    
    # Mostrar tabla para verificar datos
    st.dataframe(df)

except Exception as e:
    st.error(f"Error de conexión: {e}")   
    
