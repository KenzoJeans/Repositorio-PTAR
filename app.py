import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io

st.set_page_config(page_title="Control PTAR", layout="wide")
st.title("💧 Control de Vertimientos")

# 1. ENLACE - Verifica que sea este exactamente
SHEET_URL = "https://docs.google.com/spreadsheets/d/TU_ID_AQUÍ/edit#gid=0"

@st.cache_data(ttl=10)
def cargar_datos_seguro(url):
    # Convertir link a descarga CSV
    csv_url = url.replace('/edit#gid=', '/export?format=csv&gid=')
    
    # DESCARGA MANUAL PARA EVITAR EL ERROR DE CODEC
    response = requests.get(csv_url)
    response.encoding = 'utf-8' # Forzamos la lectura en UTF-8
    
    # Si falla el utf-8, intentamos con latin-1 automáticamente
    try:
        data = io.StringIO(response.text)
        df = pd.read_csv(data)
    except:
        df = pd.read_csv(io.StringIO(response.content.decode('latin-1', errors='ignore')))

    # Limpieza de columnas (según tu última imagen)
    df.columns = [c.strip() for c in df.columns]
    
    # Convertir números
    for col in ['ph', 'Temperatura', 'Solidos suspendidos']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    if 'Fecha' in df.columns:
        df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
        
    return df

# 2. EJECUCIÓN
try:
    df = cargar_datos_seguro(SHEET_URL)
    st.success("✅ ¡Conexión exitosa! Datos recuperados.")

    # Mostrar tabla de verificación
    st.dataframe(df.head())

    # Gráfico
    if 'ph' in df.columns and 'Fecha' in df.columns:
        fig = px.line(df, x='Fecha', y='ph', color='Proceso' if 'Proceso' in df.columns else None,
                     markers=True, title="Tendencia de pH")
        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Error persistente: {e}")
    st.info("Prueba esto: En Google Sheets, ve a Archivo > Configuración > Cambia la región a 'Estados Unidos'. A veces esto arregla el formato de exportación.")
