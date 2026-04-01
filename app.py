import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Configuración de la página
st.set_page_config(page_title="Gestión Integral PTAR", layout="wide", page_icon="💧")

st.markdown('<p style="font-size:32px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# 2. Función de limpieza (Mejorada para forzar tipos de datos)
def limpiar_datos(df):
    if df is None or df.empty:
        return pd.DataFrame()
    
    df.columns = df.columns.str.strip()
    
    mapeo = {
        'Marca temporal': 'timestamp', 'Fecha del reporte': 'fecha', 
        'Proceso a reportar': 'proceso', 'ph': 'ph', 'Temperatura': 'temp', 
        'Solidos suspendidos': 'sst', 'Caudal del vertimiento': 'caudal'
    }
    df = df.rename(columns=mapeo)

    # Forzamos conversión numérica para evitar errores de gráficas
    for col in ['ph', 'temp', 'sst', 'caudal']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha']).dt.date
    
    return df.dropna(subset=['ph']) # Solo filas con datos reales

# 3. Conexión con TTL=0 (Para forzar datos frescos)
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # ttl=0 obliga a Streamlit a no usar memoria vieja
    try:
        df_v = limpiar_datos(conn.read(worksheet="vertimiento", ttl=0))
    except:
        df_v = pd.DataFrame()

    try:
        df_t = limpiar_datos(conn.read(worksheet="tratada", ttl=0))
    except:
        df_t = pd.DataFrame()

    try:
        df_m = conn.read(worksheet="mantenimiento", ttl=0)
    except:
        df_m = pd.DataFrame()

    # --- DISEÑO DE PESTAÑAS ---
    t1, t2, t3 = st.tabs(["📊 Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with t1:
        if not df_v.empty:
            # Métricas superiores
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("pH Promedio", f"{df_v['ph'].mean():.2f}")
            m2.metric("Temp Promedio", f"{df_v['temp'].mean():.1f} °C")
            m3.metric("SST Promedio", f"{df_v['sst'].mean():.2f}")
            m4.metric("Registros", len(df_v))
            
            # Gráfica de Tendencia
            st.subheader("Tendencia de pH")
            st.line_chart(df_v.groupby('fecha')['ph'].mean())
            
            st.subheader("Datos en Crudo")
            st.dataframe(df_v, use_container_width=True)
        else:
            st.error("⚠️ No se encuentran datos en la pestaña 'vertimiento'. Revisa que la primera fila tenga los títulos de columna.")

    with t2:
        if not df_t.empty:
            st.subheader("Análisis de Agua Tratada")
            st.dataframe(df_t, use_container_width=True)
        else:
            st.info("Pestaña 'tratada' detectada pero sin registros todavía.")

    with t3:
        if not df_m.empty:
            st.subheader("Registro de Mantenimiento")
            st.dataframe(df_m, use_container_width=True)
        else:
            st.info("Pestaña 'mantenimiento' lista para recibir datos.")

except Exception as e:
    st.error(f"Error de conexión: {e}")
