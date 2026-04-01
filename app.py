import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Configuración de la interfaz
st.set_page_config(page_title="Gestión PTAR Pro", layout="wide", page_icon="💧")
st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# 2. Función de limpieza avanzada
def procesar_datos(df):
    if df is None or df.empty:
        return pd.DataFrame()
    
    # Limpiamos nombres de columnas
    df.columns = df.columns.str.strip()
    
    # Diccionario de traducción de nombres (ajusta según tus títulos reales en el Excel)
    mapeo = {
        'Marca temporal': 'timestamp', 
        'Fecha del reporte': 'fecha', 
        'Proceso a reportar': 'proceso', 
        'ph': 'ph', 
        'Temperatura': 'temp', 
        'Solidos suspendidos': 'sst'
    }
    df = df.rename(columns=mapeo)

    # Convertir a números asegurando el formato (puntos y comas)
    cols_num = ['ph', 'temp', 'sst']
    for col in cols_num:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha']).dt.date
    
    return df

# 3. Conexión y carga individual de pestañas
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Cargamos cada pestaña de forma independiente para evitar que una falle el dashboard completo
    try:
        df_v = procesar_datos(conn.read(worksheet="vertimiento", ttl=0))
    except:
        df_v = pd.DataFrame()

    try:
        df_t = procesar_datos(conn.read(worksheet="tratada", ttl=0))
    except:
        df_t = pd.DataFrame()

    try:
        df_m = conn.read(worksheet="mantenimiento", ttl=0)
    except:
        df_m = pd.DataFrame()

    # --- PESTAÑAS DEL DASHBOARD ---
    t1, t2, t3 = st.tabs(["📊 Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with t1:
        if not df_v.empty and 'ph' in df_v.columns:
            # Métricas
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("pH Promedio", f"{df_v['ph'].mean():.2f}")
            c2.metric("Temp Promedio", f"{df_v['temp'].mean():.1f} °C")
            c3.metric("SST Promedio", f"{df_v['sst'].mean():.2f}")
            c4.metric("Registros", len(df_v))
            
            # Gráfica
            st.subheader("Análisis de Tendencia")
            st.line_chart(df_v.groupby('fecha')['ph'].mean())
            st.dataframe(df_v, use_container_width=True)
        else:
            st.error("⚠️ No hay datos en 'vertimiento'. Revisa que la Fila 1 tenga los títulos.")

    with t2:
        if not df_t.empty:
            st.subheader("Resultados Agua Tratada")
            st.dataframe(df_t, use_container_width=True)
        else:
            st.info("ℹ️ Esperando datos en la pestaña 'tratada'.")

    with t3:
        if not df_m.empty:
            st.subheader("Bitácora de Equipos")
            st.dataframe(df_m, use_container_width=True)
        else:
            st.info("ℹ️ No hay mantenimientos registrados aún.")

except Exception as e:
    st.error(f"Error crítico: {e}")
