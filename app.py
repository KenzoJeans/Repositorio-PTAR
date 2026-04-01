import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Configuración inicial
st.set_page_config(page_title="Gestión PTAR", layout="wide", page_icon="💧")
st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# Función de limpieza robusta
def procesar_hoja(df):
    if df is None or df.empty:
        return pd.DataFrame()
    
    # Limpiar espacios en los títulos
    df.columns = df.columns.str.strip()
    
    # Mapeo flexible (busca el nombre aunque cambie un poco)
    mapeo = {
        'Marca temporal': 'timestamp', 
        'Fecha del reporte': 'fecha', 
        'Proceso a reportar': 'proceso', 
        'ph': 'ph', 
        'Temperatura': 'temp', 
        'Solidos suspendidos': 'sst',
        'Caudal del vertimiento': 'caudal'
    }
    df = df.rename(columns=mapeo)

    # Convertir a números (maneja comas y puntos)
    for col in ['ph', 'temp', 'sst', 'caudal']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha']).dt.date
    
    return df

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # TTL=0 obliga a leer el Excel real ahora mismo
    df_v = procesar_hoja(conn.read(worksheet="vertimiento", ttl=0))
    df_t = procesar_hoja(conn.read(worksheet="tratada", ttl=0))
    df_m = conn.read(worksheet="mantenimiento", ttl=0)

    t1, t2, t3 = st.tabs(["📊 Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with t1:
        if not df_v.empty and 'ph' in df_v.columns:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("pH Promedio", f"{df_v['ph'].mean():.2f}")
            c2.metric("Temp Promedio", f"{df_v['temp'].mean():.1f} °C")
            c3.metric("SST Promedio", f"{df_v['sst'].mean():.2f}")
            c4.metric("Registros", len(df_v))
            
            st.subheader("Tendencia Histórica")
            st.line_chart(df_v.groupby('fecha')['ph'].mean())
            st.dataframe(df_v, use_container_width=True)
        else:
            st.error("⚠️ Verifica que la pestaña 'vertimiento' tenga los títulos en la Fila 1.")

    with t2:
        st.info("Pestaña 'tratada' lista. Registra datos para ver el análisis de eficiencia.")
        if not df_t.empty: st.dataframe(df_t)

    with t3:
        st.info("Pestaña 'mantenimiento' lista para bitácora de equipos.")
        if not df_m.empty: st.dataframe(df_m)

except Exception as e:
    st.error(f"Error de conexión: {e}")
