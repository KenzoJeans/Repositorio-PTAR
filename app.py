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
    # Truco para convertir el link de edición en link de descarga CSV
    csv_url = url.replace('/edit#gid=', '/export?format=csv&gid=')
    df = pd.read_csv(csv_url)
    
    # Limpieza de espacios en los nombres de las columnas
    df.columns = [c.strip() for c in df.columns]
    
    # Renombrado inteligente por palabras clave
    nuevos_nombres = {}
    for col in df.columns:
        if 'Fecha' in col: nuevos_nombres[col] = 'Fecha'
        elif 'Proceso' in col: nuevos_nombres[col] = 'Proceso'
        elif 'pH' in col: nuevos_nombres[col] = 'pH'
        elif 'Temperatura' in col: nuevos_nombres[col] = 'Temp'
        elif 'Sólidos' in col or 'Solidos' in col: nuevos_nombres[col] = 'Solidos'
    
    df = df.rename(columns=nuevos_nombres)
    
    # Limpieza de datos (Comas a Puntos y convertir a números)
    for col in ['pH', 'Temp', 'Solidos']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '.').astype(float)
            
    # Convertir fecha
    if 'Fecha' in df.columns:
        df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True)
    
    return df

# 2. EJECUCIÓN DEL PROGRAMA
try:
    df = cargar_desde_sheets(SHEET_URL)
    st.success("✅ Datos sincronizados correctamente")

    # --- FILTROS ---
    st.sidebar.header("Filtros")
    if 'Proceso' in df.columns:
        procesos = st.sidebar.multiselect("Filtrar Procesos:", 
                                         options=df['Proceso'].unique(), 
                                         default=df['Proceso'].unique())
        df_filt = df[df['Proceso'].isin(procesos)]
    else:
        df_filt = df

    # --- KPIs ---
    col1, col2, col3 = st.columns(3)
    if 'pH' in df_filt.columns:
        col1.metric("pH Promedio", f"{df_filt['pH'].mean():.2f}")
    if 'Temp' in df_filt.columns:
        col2.metric("Temp. Promedio", f"{df_filt['Temp'].mean():.1f} °C")
    if 'Solidos' in df_filt.columns:
        col3.metric("Sólidos Prom.", f"{df_filt['Solidos'].mean():.1f}")

    # --- GRÁFICO ---
    if 'pH' in df_filt.columns and 'Fecha' in df_filt.columns:
        fig = px.line(df_filt, x='Fecha', y='pH', color='Proceso' if 'Proceso' in df_filt.columns else None,
                     markers=True, title="Tendencia de pH", template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Hubo un problema al procesar los datos: {e}")
    st.info("Revisa que el enlace de Google Sheets sea correcto y público.")
