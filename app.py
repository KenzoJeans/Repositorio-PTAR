import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Control PTAR", layout="wide")
st.title("💧 Control de Vertimientos (Tiempo Real)")

# --- REEMPLAZA EL ENLACE DE ABAJO POR EL TUYO ---
# Asegúrate de que termine en /edit#gid=...
SHEET_URL = "https://docs.google.com/spreadsheets/d/TU_ID_AQUÍ/edit#gid=0"

@st.cache_data(ttl=60)
def cargar_datos_seguro(url):
    # Transformamos el link para descarga directa
    csv_url = url.replace('/edit#gid=', '/export?format=csv&gid=')
    
    try:
        # Descarga manual para evitar errores de codificación (ASCII/UTF-8)
        response = requests.get(csv_url)
        
        # Si Google nos devuelve HTML, es porque el archivo NO es público
        if "<!DOCTYPE html>" in response.text:
            st.error("🚨 Error de Acceso: El Google Sheet no es público.")
            st.info("Ve a tu Sheet > Compartir > Cambia a 'Cualquier persona con el enlace'.")
            st.stop()
            
        # Forzamos la lectura correcta de caracteres en español
        response.encoding = 'utf-8'
        df = pd.read_csv(io.StringIO(response.text))
        
        # Limpieza de nombres de columnas (quitar espacios invisibles)
        df.columns = [c.strip() for c in df.columns]
        
        # Conversión de datos numéricos (ajustado a tus nuevos nombres de columna)
        columnas_numericas = ['ph', 'Temperatura', 'Solidos suspendidos']
        for col in columnas_numericas:
            if col in df.columns:
                # Reemplazamos coma por punto para que Python lo entienda como número
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
        
        # Conversión de fecha
        if 'Fecha' in df.columns:
            df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
            
        return df

    except Exception as e:
        st.error(f"Fallo en la descarga: {e}")
        st.stop()

# 2. EJECUCIÓN DEL DASHBOARD
try:
    df = cargar_datos_seguro(SHEET_URL)
    
    st.success("✅ Datos sincronizados correctamente")

    # --- FILTROS EN BARRA LATERAL ---
    st.sidebar.header("Opciones de Visualización")
    if 'Proceso' in df.columns:
        lista_procesos = df['Proceso'].dropna().unique()
        seleccion = st.sidebar.multiselect("Seleccionar Proceso:", 
                                          options=lista_procesos, 
                                          default=lista_procesos)
        df_filt = df[df['Proceso'].isin(seleccion)]
    else:
        df_filt = df

    # --- MÉTRICAS PRINCIPALES ---
    col1, col2, col3 = st.columns(3)
    if 'ph' in df_filt.columns:
        col1.metric("pH Promedio", f"{df_filt['ph'].mean():.2f}")
    if 'Temperatura' in df_filt.columns:
        col2.metric("Temp. Promedio", f"{df_filt['Temperatura'].mean():.1f} °C")
    if 'Solidos suspendidos' in df_filt.columns:
        col3.metric("Sólidos Promedio", f"{df_filt['Solidos suspendidos'].mean():.1f} mg/L")

    # --- GRÁFICO DE TENDENCIA ---
    st.markdown("### Histórico de Parámetros")
    parametro = st.selectbox("Selecciona el parámetro a graficar:", ['ph', 'Temperatura', 'Solidos suspendidos'])
    
    if parametro in df_filt.columns and 'Fecha' in df_filt.columns:
        fig = px.line(df_filt, 
                     x='Fecha', 
                     y=parametro, 
                     color='Proceso' if 'Proceso' in df_filt.columns else None,
                     markers=True,
                     template="plotly_white",
                     title=f"Evolución de {parametro} en el tiempo")
        st.plotly_chart(fig, use_container_width=True)

    # --- TABLA DE DATOS ---
    with st.expander("Ver tabla de datos completa"):
        st.dataframe(df_filt)

except Exception as e:
    st.error(f"Error al procesar el dashboard: {e}")
