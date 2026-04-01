import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Configuración de la interfaz
st.set_page_config(page_title="Gestión PTAR Pro", layout="wide", page_icon="💧")
st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# 2. Función de limpieza (La que te funcionaba bien)
def limpiar_datos_seguro(df):
    if df is None or df.empty:
        return pd.DataFrame()
    
    df.columns = df.columns.str.strip()
    
    # Mapeo manual para asegurar que las métricas encuentren sus columnas
    mapeo = {
        'ph': 'ph', 'pH': 'ph', 'PH': 'ph',
        'Temperatura': 'temp', 'temp': 'temp', 'TEMP': 'temp',
        'Solidos suspendidos': 'sst', 'sst': 'sst', 'SST': 'sst',
        'Fecha del reporte': 'fecha', 'fecha': 'fecha'
    }
    
    # Renombrar solo las que existan
    columnas_a_renombrar = {k: v for k, v in mapeo.items() if k in df.columns}
    df = df.rename(columns=columnas_a_renombrar)

    # Conversión numérica estricta
    for col in ['ph', 'temp', 'sst']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    return df

# 3. Conexión Principal
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # NAVEGACIÓN POR PESTAÑAS (Streamlit maneja la interfaz, nosotros los datos)
    t1, t2, t3 = st.tabs(["📊 Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with t1:
        # Intentamos leer la pestaña específica; si falla, intentamos la carga general
        try:
            data_raw = conn.read(worksheet="vertimiento", ttl=0)
            df_v = limpiar_datos_seguro(data_raw)
        except Exception:
            st.warning("No se pudo leer la pestaña 'vertimiento'. Intentando carga por defecto...")
            df_v = limpiar_datos_seguro(conn.read(ttl=0))

        if not df_v.empty:
            # Filtro de Proceso (El que tenías en el sidebar)
            if 'Proceso a reportar' in df_v.columns:
                procesos = df_v['Proceso a reportar'].unique().tolist()
                sel = st.multiselect("Filtrar por Proceso:", procesos, default=procesos)
                df_v = df_v[df_v['Proceso a reportar'].isin(sel)]

            # Métricas
            c1, c2, c3 = st.columns(3)
            if 'ph' in df_v.columns:
                c1.metric("Promedio pH", f"{df_v['ph'].mean():.2f}")
            if 'temp' in df_v.columns:
                c2.metric("Temp Promedio", f"{df_v['temp'].mean():.1f} °C")
            c3.metric("Registros", len(df_v))

            st.subheader("Visualización de Datos")
            st.dataframe(df_v, use_container_width=True)
        else:
            st.error("Error: No se detectaron datos legibles en el origen.")

    with t2:
        st.info("Para activar esta pestaña, asegúrate de que la hoja 'tratada' tenga al menos una fila de datos.")
        try:
            df_t = conn.read(worksheet="tratada", ttl=0)
            st.write(df_t)
        except:
            st.write("Esperando conexión con la pestaña 'tratada'...")

    with t3:
        st.info("Pestaña de mantenimiento configurada.")
        try:
            df_m = conn.read(worksheet="mantenimiento", ttl=0)
            st.write(df_m)
        except:
            st.write("Esperando conexión con la pestaña 'mantenimiento'...")

except Exception as e:
    st.error(f"Error general: {e}")
