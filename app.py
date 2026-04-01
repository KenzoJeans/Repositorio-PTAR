import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Configuración de la página
st.set_page_config(page_title="Gestión Integral PTAR", layout="wide", page_icon="💧")

st.markdown('<p style="font-size:32px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# 2. Función de limpieza
def limpiar_datos(df):
    if df is None or df.empty:
        return pd.DataFrame()
    df.columns = df.columns.str.strip()
    
    # Mapeo según tus columnas actuales
    mapeo = {
        'Marca temporal': 'timestamp', 'Fecha del reporte': 'fecha', 
        'Proceso a reportar': 'proceso', 'ph': 'ph', 'Temperatura': 'temp', 
        'Solidos suspendidos': 'sst', 'Caudal del vertimiento': 'caudal'
    }
    df = df.rename(columns=mapeo)

    # Conversión a números
    cols_num = ['ph', 'temp', 'sst', 'caudal']
    for col in cols_num:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha']).dt.date
    return df

# 3. Conexión y Carga de Datos
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # IMPORTANTE: Aquí usamos los nombres exactos de tu imagen
    try:
        df_v = limpiar_datos(conn.read(worksheet="vertimiento"))
    except:
        df_v = pd.DataFrame()

    try:
        df_t = limpiar_datos(conn.read(worksheet="tratada"))
    except:
        df_t = pd.DataFrame()

    try:
        df_m = conn.read(worksheet="mantenimiento")
    except:
        df_m = pd.DataFrame()

    # --- NAVEGACIÓN ---
    t1, t2, t3 = st.tabs(["📊 Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with t1:
        if not df_v.empty:
            # Métricas
            c1, c2, c3 = st.columns(3)
            c1.metric("pH Promedio", f"{df_v['ph'].mean():.2f}")
            c2.metric("Temp Promedio", f"{df_v['temp'].mean():.1f} °C")
            c3.metric("Total Reportes", len(df_v))
            
            # Gráfica
            st.subheader("Tendencia de pH")
            st.line_chart(df_v.groupby('fecha')['ph'].mean())
            
            st.subheader("Detalle de Registros")
            st.dataframe(df_v, use_container_width=True)
        else:
            st.warning("No se pudieron cargar datos de la pestaña 'vertimiento'.")

    with t2:
        if not df_t.empty:
            st.subheader("Datos de Agua Tratada")
            st.dataframe(df_t, use_container_width=True)
        else:
            st.info("La pestaña 'tratada' está vacía o no tiene el formato correcto.")

    with t3:
        if not df_m.empty:
            st.subheader("Historial de Mantenimiento")
            st.dataframe(df_m, use_container_width=True)
        else:
            st.info("La pestaña 'mantenimiento' está vacía o no se detecta.")

except Exception as e:
    st.error(f"Error de conexión: {e}")
