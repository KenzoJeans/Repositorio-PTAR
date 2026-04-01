import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Configuración
st.set_page_config(page_title="Gestión PTAR Pro", layout="wide", page_icon="💧")
st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# 2. Función de Procesamiento por Posición
def procesar_por_posicion(df):
    if df is None or df.empty:
        return pd.DataFrame()
    
    # Forzamos los nombres basados en el orden típico de tu Sheet
    # 0: Marca temporal, 1: Fecha, 2: Proceso, 3: pH, 4: Temp, 5: SST...
    nuevos_nombres = {}
    columnas_actuales = df.columns.tolist()
    
    mapeo_orden = {
        1: 'fecha',
        2: 'proceso',
        3: 'ph',
        4: 'temp',
        5: 'sst'
    }
    
    for i, nombre in enumerate(columnas_actuales):
        if i in mapeo_orden:
            nuevos_nombres[nombre] = mapeo_orden[i]
            
    df = df.rename(columns=nuevos_nombres)

    # Limpieza de números
    for col in ['ph', 'temp', 'sst']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce').dt.date
        
    return df.dropna(subset=['ph'])

# 3. Conexión
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Intentar cargar vertimiento (usando ttl=0 para datos frescos)
    df_v = procesar_por_posicion(conn.read(worksheet="vertimiento", ttl=0))
    
    t1, t2, t3 = st.tabs(["📊 Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with t1:
        if not df_v.empty:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("pH Promedio", f"{df_v['ph'].mean():.2f}")
            c2.metric("Temp Promedio", f"{df_v['temp'].mean():.1f} °C")
            c3.metric("SST Promedio", f"{df_v['sst'].mean():.2f}")
            c4.metric("Registros", len(df_v))
            
            st.subheader("Análisis de Tendencia")
            st.line_chart(df_v.groupby('fecha')['ph'].mean())
            st.dataframe(df_v, use_container_width=True)
        else:
            st.error("⚠️ No se detectan datos. Revisa que la pestaña se llame 'vertimiento' en minúsculas.")
            # Auxilio visual para debug:
            if st.checkbox("Ver nombres de columnas detectados"):
                raw_df = conn.read(worksheet="vertimiento", ttl=0)
                st.write(raw_df.columns.tolist())

    with t2:
        st.info("Pestaña 'tratada' activa.")

    with t3:
        st.info("Pestaña 'mantenimiento' activa.")

except Exception as e:
    st.error(f"Error de conexión: {e}")
