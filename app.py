import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Control PTAR", layout="wide")
st.title("💧 Control de Vertimientos")

# 1. ENLACE (Asegúrate de que este sea tu link)
SHEET_URL = "https://docs.google.com/spreadsheets/d/TU_ID_AQUÍ/edit#gid=0"

@st.cache_data(ttl=10)
def cargar_datos(url):
    csv_url = url.replace('/edit#gid=', '/export?format=csv&gid=')
    
    # Probamos con 'latin-1' que es más permisivo con archivos de Sheets/Excel
    df = pd.read_csv(csv_url, encoding='latin-1', on_bad_lines='skip')
    
    # Limpiamos espacios invisibles en los nombres de las columnas
    df.columns = [c.strip() for c in df.columns]
    
    # Convertimos los números (manejando puntos o comas)
    # Ajustado a tus nuevos nombres: 'ph', 'Temperatura', 'Solidos suspendidos'
    for col in ['ph', 'Temperatura', 'Solidos suspendidos']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    if 'Fecha' in df.columns:
        df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
        
    return df

# 2. EJECUCIÓN
try:
    df = cargar_datos(SHEET_URL)
    
    # Esto nos confirmará qué columnas está leyendo realmente
    st.success(f"✅ Conectado. Columnas detectadas: {list(df.columns)}")

    # Filtro de Proceso
    if 'Proceso' in df.columns:
        proc = st.sidebar.multiselect("Filtrar Proceso:", df['Proceso'].unique(), default=df['Proceso'].unique())
        df = df[df['Proceso'].isin(proc)]

    # Gráfico de pH
    if 'ph' in df.columns and 'Fecha' in df.columns:
        fig = px.line(df, x='Fecha', y='ph', color='Proceso' if 'Proceso' in df.columns else None,
                     markers=True, title="Evolución de pH")
        st.plotly_chart(fig, use_container_width=True)
        
    st.write("### Tabla de Datos Actualizados", df)

except Exception as e:
    st.error(f"Error crítico: {e}")
