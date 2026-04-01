import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Configuración de la interfaz
st.set_page_config(page_title="Gestión PTAR Pro", layout="wide", page_icon="💧")
st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# 2. Función de Limpieza Inteligente (Busca coincidencias parciales)
def procesar_datos_ptar(df):
    if df is None or df.empty:
        return pd.DataFrame()
    
    # Limpiamos nombres de columnas originales
    df.columns = [str(c).strip() for c in df.columns]
    
    # Mapeo por palabras clave para no fallar por una letra
    columnas_finales = {}
    for col in df.columns:
        c_low = col.lower()
        if 'ph' in c_low: columnas_finales[col] = 'ph'
        elif 'temp' in c_low: columnas_finales[col] = 'temp'
        elif 'solido' in c_low or 'sst' in c_low: columnas_finales[col] = 'sst'
        elif 'proceso' in c_low: columnas_finales[col] = 'proceso'
        elif 'fecha' in c_low: columnas_finales[col] = 'fecha'
        elif 'caudal' in c_low: columnas_finales[col] = 'caudal'
    
    df = df.rename(columns=columnas_finales)

    # Convertir a números (limpiando comas y puntos)
    for col in ['ph', 'temp', 'sst', 'caudal']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    # Manejo de fechas
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce').dt.date
    
    return df

# 3. Conexión y carga
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Leemos con nombres de pestañas en minúsculas (según tu imagen previa)
    try:
        df_v = procesar_datos_ptar(conn.read(worksheet="vertimiento", ttl=0))
    except:
        df_v = pd.DataFrame()

    try:
        df_t = procesar_datos_ptar(conn.read(worksheet="tratada", ttl=0))
    except:
        df_t = pd.DataFrame()

    try:
        df_m = conn.read(worksheet="mantenimiento", ttl=0)
    except:
        df_m = pd.DataFrame()

    # --- PESTAÑAS ---
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
            st.subheader("Análisis de Tendencia (pH)")
            if not df_v['fecha'].isnull().all():
                st.line_chart(df_v.groupby('fecha')['ph'].mean())
            
            st.subheader("Vista de Datos")
            st.dataframe(df_v, use_container_width=True)
        else:
            st.error("⚠️ El sistema no logra identificar las columnas en la pestaña 'vertimiento'.")
            st.info("Asegúrate de que los títulos estén en la Fila 1 de la hoja 'vertimiento'.")

    with t2:
        if not df_t.empty:
            st.subheader("Resultados Agua Tratada")
            st.dataframe(df_t, use_container_width=True)
        else:
            st.info("Esperando datos en la pestaña 'tratada'.")

    with t3:
        if not df_m.empty:
            st.subheader("Bitácora de Mantenimiento")
            st.dataframe(df_m, use_container_width=True)
        else:
            st.info("No hay registros en la pestaña 'mantenimiento'.")

except Exception as e:
    st.error(f"Error de conexión: {e}")
