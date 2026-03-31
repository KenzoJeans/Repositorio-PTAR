import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURACIÓN
st.set_page_config(page_title="PTAR Real-Time", layout="wide")
st.title("💧 Control de Vertimientos (Tiempo Real)")

# --- REEMPLAZA EL ENLACE DE ABAJO POR EL TUYO ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/TU_ID_AQUÍ/edit#gid=0"

@st.cache_data(ttl=600)
def cargar_desde_sheets(url):
    # Formatear el link para que sea un CSV descargable
    csv_url = url.replace('/edit#gid=', '/export?format=csv&gid=')
    
    # LEER CON UTF-8 PARA EVITAR EL ERROR DE LAS TILDES
    df = pd.read_csv(csv_url, encoding='utf-8')
    
    # Limpiar nombres de columnas (quitar espacios invisibles)
    df.columns = [c.strip() for c in df.columns]
    
    # Renombrar columnas largas por palabras clave
    nuevos_nombres = {}
    for col in df.columns:
        if 'Fecha' in col: nuevos_nombres[col] = 'Fecha'
        elif 'Proceso' in col: nuevos_nombres[col] = 'Proceso'
        elif 'pH' in col: nuevos_nombres[col] = 'pH'
        elif 'Temperatura' in col: nuevos_nombres[col] = 'Temp'
        elif 'Sólidos' in col or 'Solidos' in col: nuevos_nombres[col] = 'Solidos'
    
    df = df.rename(columns=nuevos_nombres)
    
    # Convertir números: cambiar comas por puntos
    for col in ['pH', 'Temp', 'Solidos']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '.').astype(float)
            
    # Formatear la fecha
    if 'Fecha' in df.columns:
        df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True)
    
    return df

# 2. EJECUCIÓN DEL DASHBOARD
try:
    df = cargar_desde_sheets(SHEET_URL)
    st.success("✅ Datos sincronizados correctamente")

    # Muestra los datos crudos para verificar
    with st.expander("Ver previsualización de la tabla"):
        st.dataframe(df.head())

    # --- INDICADORES Y GRÁFICO ---
    col1, col2, col3 = st.columns(3)
    if 'pH' in df.columns:
        col1.metric("pH Promedio", f"{df['pH'].mean():.2f}")
    if 'Temp' in df.columns:
        col2.metric("Temp. Promedio", f"{df['Temp'].mean():.1f} °C")
    if 'Solidos' in df.columns:
        col3.metric("Sólidos Prom.", f"{df['Solidos'].mean():.1f} mg/L")

    st.plotly_chart(px.line(df, x='Fecha', y='pH', color='Proceso' if 'Proceso' in df.columns else None,
                          markers=True, title="Histórico de pH", template="plotly_white"), use_container_width=True)

except Exception as e:
    st.error(f"Hubo un problema: {e}")
