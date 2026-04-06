import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Sistema Control PTAR", layout="wide", page_icon="💧")
st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# 2. FUNCIÓN DE LIMPIEZA ROBUSTA
def limpiar_datos(df):
    if df is None or df.empty:
        return pd.DataFrame()
    df.columns = df.columns.str.strip() # Quita espacios invisibles
    return df

# 3. CONEXIÓN
try:
    conn = st.connection("gsheets", type=GSheetsConnection)

    t1, t2, t3 = st.tabs(["📊 Dashboard Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    # --- PESTAÑA 1: VERTIMIENTO ---
    with t1:
        try:
            # Forzamos ttl=0 para que no use datos viejos de la caché
            df_v = conn.read(worksheet="vertimiento", ttl=0)
            df_v = limpiar_datos(df_v)
            if not df_v.empty:
                st.success("Datos de 'vertimiento' cargados.")
                st.dataframe(df_v.head())
            else:
                st.warning("La hoja 'vertimiento' está vacía.")
        except Exception as e:
            st.error("No se encontró la pestaña 'vertimiento'.")
            st.info("Revisa que en Google Sheets el nombre sea exactamente 'vertimiento' (en minúsculas y sin espacios).")

    # --- PESTAÑA 2: AGUA TRATADA ---
    with t2:
        try:
            df_t = conn.read(worksheet="tratada", ttl=0)
            st.dataframe(limpiar_datos(df_t))
        except:
            st.info("Pestaña 'tratada' no disponible.")

    # --- PESTAÑA 3: MANTENIMIENTO ---
    with t3:
        st.subheader("🛠️ Bitácora de Mantenimiento")
        try:
            # Intentamos leer la pestaña 'mantenimiento'
            df_m = conn.read(worksheet="mantenimiento", ttl=0)
            df_m = limpiar_datos(df_m)
            
            if not df_m.empty:
                # Si carga datos de pH, es que Google Sheets está enviando la hoja equivocada
                if 'PH' in df_m.columns or 'ph' in df_m.columns:
                    st.error("⚠️ Error: Se están cargando datos de Vertimientos aquí.")
                else:
                    st.success("Datos de Mantenimiento cargados correctamente.")
                    st.dataframe(df_m)
            else:
                st.info("La hoja 'mantenimiento' está vacía.")
        except Exception as e:
            st.error("Error al acceder a 'mantenimiento'.")
            st.code("Posible solución: Asegúrate de que la URL en secrets incluya el ID correcto.")

except Exception as e:
    st.error(f"Error general de conexión: {e}")
