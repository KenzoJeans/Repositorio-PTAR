import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Dashboard PTAR", layout="wide")
st.title("💧 Control de Vertimientos Industrial")

# --- CONEXIÓN CON SECRETS ---
# Aquí usamos el nombre que le hayas puesto en Streamlit Cloud (ej: "gsheets_url")
try:
    SHEET_URL = st.secrets["gsheets_url"]
except:
    st.error("No se encontró la variable 'gsheets_url' en los Secrets de Streamlit.")
    st.stop()

@st.cache_data(ttl=60)
def cargar_datos(url):
    try:
        # Convertimos el link a formato exportación CSV por si pegaste el link de edición
        if "/edit" in url:
            url = url.split('/edit')[0] + '/export?format=csv'
            if "gid=" in st.secrets["gsheets_url"]:
                gid = st.secrets["gsheets_url"].split("gid=")[1]
                url += f"&gid={gid}"

        response = requests.get(url)
        response.encoding = 'utf-8'
        
        # Si devuelve HTML, hay un problema de permisos en el Sheet
        if "<!DOCTYPE html>" in response.text:
            st.error("🚨 Error de acceso: Verifica que el Sheet esté como 'Cualquier persona con el enlace'.")
            st.stop()

        df = pd.read_csv(io.StringIO(response.text))
        
        # Limpieza estándar
        df.columns = [c.strip() for c in df.columns]
        
        # Conversión de parámetros PTAR
        for col in ['ph', 'Temperatura', 'Solidos suspendidos']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
        
        if 'Fecha' in df.columns:
            df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
            
        return df
    except Exception as e:
        st.error(f"Error técnico al cargar datos: {e}")
        return None

# 2. EJECUCIÓN
df = cargar_datos(SHEET_URL)

if df is not None:
    # --- FILTROS LATERALES ---
    st.sidebar.header("Panel de Control")
    procesos = df['Proceso'].dropna().unique() if 'Proceso' in df.columns else []
    sel_proceso = st.sidebar.multiselect("Filtrar por Proceso:", procesos, default=procesos)
    df_filt = df[df['Proceso'].isin(sel_proceso)]

    # --- MÉTRICAS DE RESUMEN ---
    m1, m2, m3 = st.columns(3)
    if 'ph' in df_filt.columns:
        m1.metric("Promedio pH", f"{df_filt['ph'].mean():.2f}")
    if 'Temperatura' in df_filt.columns:
        m2.metric("Promedio Temp.", f"{df_filt['Temperatura'].mean():.1f} °C")
    if 'Solidos suspendidos' in df_filt.columns:
        m3.metric("Promedio Sólidos", f"{df_filt['Solidos suspendidos'].mean():.1f} mg/L")

    # --- PESTAÑAS DE ANÁLISIS ---
    tab1, tab2, tab3 = st.tabs(["📈 Histórico", "📊 Comparativa", "🧪 Correlación"])

    with tab1:
        st.subheader("Tendencia Temporal")
        param = st.selectbox("Variable a visualizar:", ['ph', 'Temperatura', 'Solidos suspendidos'])
        fig_linea = px.line(df_filt, x='Fecha', y=param, color='Proceso', markers=True, template="plotly_white")
        st.plotly_chart(fig_linea, use_container_width=True)

    with tab2:
        st.subheader("Distribución por Proceso")
        # Gráfico de barras del promedio de sólidos
        avg_solids = df_filt.groupby('Proceso')['Solidos suspendidos'].mean().reset_index()
        fig_barra = px.bar(avg_solids, x='Proceso', y='Solidos suspendidos', color='Proceso', text_auto='.1f', title="Carga de Sólidos por Tipo de Proceso")
        st.plotly_chart(fig_barra, use_container_width=True)

    with tab3:
        st.subheader("Análisis de Variables")
        # Relación pH y Temperatura, el tamaño del punto son los Sólidos
        fig_scatter = px.scatter(df_filt, x='Temperatura', y='ph', color='Proceso', 
                                 size='Solidos suspendidos', hover_data=['Fecha'],
                                 title="Relación pH vs Temperatura (Tamaño = Sólidos)")
        st.plotly_chart(fig_scatter, use_container_width=True)

    with st.expander("📂 Explorar Base de Datos Completa"):
        st.dataframe(df_filt)
