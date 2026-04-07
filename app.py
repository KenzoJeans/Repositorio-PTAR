import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 1. Configuración de página
st.set_page_config(page_title="Sistema Control PTAR", layout="wide", page_icon="💧")
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)
st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# 2. Función de limpieza de datos (Pestaña Vertimiento)
def limpiar_datos_ptar(df):
    if df is None or df.empty:
        return pd.DataFrame()
    
    df.columns = df.columns.str.strip()
    mapeo = {
        'ph': 'ph', 'pH': 'ph', 'PH': 'ph',
        'temp': 'temp', 'Temperatura': 'temp',
        'sst': 'sst', 'Solidos suspendidos': 'sst',
        'Fecha del reporte': 'fecha', 'fecha': 'fecha',
        'Proceso a reportar': 'proceso',
        'Productos quimicos utilizados en el proceso': 'quimicos'
    }
    df = df.rename(columns={k: v for k, v in mapeo.items() if k in df.columns})

    for col in ['ph', 'temp', 'sst']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce').dt.date
    
    return df.dropna(subset=['ph'])

# 3. Conexión y Carga de Datos
# IMPORTANTE: Copia aquí la URL de la pestaña de mantenimiento de tu navegador
URL_DIRECTA_MANTO = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=746789412#gid=746789412"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Carga Vertimiento (Hoja por defecto de la URL en Secrets)
    df_raw = conn.read(ttl=0) 
    df_base = limpiar_datos_ptar(df_raw)

    # Carga Mantenimiento (Usando el GID específico para evitar el Error 400)
    if "gid=" in URL_DIRECTA_MANTO:
        df_manto = conn.read(spreadsheet=URL_DIRECTA_MANTO, ttl=0)
    else:
        df_manto = pd.DataFrame()
        st.warning("Por favor, ingresa una URL válida con el parámetro 'gid' para Mantenimiento.")

    # --- INTERFAZ ---
    t1, t2, t3 = st.tabs(["📊 Dashboard Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with t1:
        if not df_base.empty:
            # Filtros rápidos (simplificados para probar conexión)
            st.subheader("📋 Detalle de Vertimientos")
            st.dataframe(df_base, use_container_width=True)
            
            # Métricas
            m1, m2 = st.columns(2)
            m1.metric("Promedio pH", f"{df_base['ph'].mean():.2f}")
            m2.metric("Total Registros", len(df_base))
        else:
            st.info("Esperando datos de Vertimientos...")

    with t2:
        st.info("Módulo de Agua Tratada en desarrollo.")

    with t3:
        st.subheader("🛠️ Registro de Actividades de Mantenimiento")
        if not df_manto.empty:
            st.success("¡Datos de mantenimiento cargados con éxito!")
            st.dataframe(df_manto, use_container_width=True)
        else:
            st.warning("No se pudieron cargar los datos de Mantenimiento. Verifica la URL directa.")

except Exception as e:
    st.error(f"Error en la aplicación: {e}")
