import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Configuración de la aplicación
st.set_page_config(page_title="Sistema Control PTAR", layout="wide", page_icon="💧")

st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# 2. Conexión a Google Sheets
try:
    # Se establece la conexión con ttl=0 para evitar datos obsoletos en caché
    conn = st.connection("gsheets", type=GSheetsConnection)

    # Definición de pestañas en la interfaz
    t1, t2, t3 = st.tabs(["📊 Dashboard Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    # --- PESTAÑA 1: VERTIMIENTO ---
    with t1:
        try:
            # Se usa el nombre exacto de la pestaña visto en tus capturas
            df_v = conn.read(worksheet="vertimiento", ttl=0)
            if not df_v.empty:
                st.success("Datos de 'vertimiento' cargados correctamente.")
                st.dataframe(df_v)
            else:
                st.warning("La hoja 'vertimiento' está vacía.")
        except Exception:
            st.error("Error: No se encontró la pestaña 'vertimiento'.")

    # --- PESTAÑA 2: AGUA TRATADA ---
    with t2:
        try:
            df_t = conn.read(worksheet="tratada", ttl=0)
            st.dataframe(df_t)
        except Exception:
            st.info("Pestaña 'tratada' no disponible o vacía.")

    # --- PESTAÑA 3: MANTENIMIENTO ---
    with t3:
        st.subheader("🛠️ Bitácora de Mantenimiento")
        try:
            # IMPORTANTE: El nombre debe coincidir exactamente con el del Excel
            df_m = conn.read(worksheet="mantenimiento", ttl=0)
            
            # Validación para evitar que se carguen datos de vertimiento por error
            if not df_m.empty:
                columnas = [str(c).upper() for c in df_m.columns]
                if 'PH' in columnas:
                    st.error("⚠️ Los datos cargados pertenecen a 'vertimiento'. Revisa el orden de las pestañas.")
                else:
                    st.success("Datos de Mantenimiento cargados.")
                    st.dataframe(df_m)
            else:
                st.info("La hoja 'mantenimiento' está vacía.")
        except Exception:
            st.error("Error al acceder a 'mantenimiento'.")

except Exception as e:
    st.error(f"Error general de conexión: {e}")
