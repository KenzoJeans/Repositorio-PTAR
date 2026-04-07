import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Sistema Control PTAR", layout="wide")

# Título
st.title("🏗️ Diagnóstico de Conexión PTAR")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # INTENTO 1: Leer la hoja por defecto (sin especificar nombre)
    st.write("### Intentando leer hoja por defecto...")
    df_default = conn.read(ttl=0)
    if not df_default.empty:
        st.success("✅ ¡Conexión exitosa con la hoja principal!")
        st.dataframe(df_default.head(5))
    
    # INTENTO 2: Leer usando la URL completa de la pestaña (Si el nombre falla)
    # Solo si el anterior funcionó, intentamos forzar la de mantenimiento
    st.write("---")
    st.write("### Intentando leer 'mantenimiento'...")
    df_manto = conn.read(worksheet="mantenimiento", ttl=0)
    st.success("✅ ¡Conexión exitosa con mantenimiento!")
    st.dataframe(df_manto.head(5))

except Exception as e:
    st.error(f"Error detectado: {e}")
    st.info("""
    **Posibles causas del Error 400:**
    1. **URL en Secrets:** Asegúrate de que la URL en `.streamlit/secrets.toml` termine en `/edit?usp=sharing` o similar, no en `/view`.
    2. **Pestañas ocultas:** Verifica que 'vertimiento' y 'mantenimiento' no estén ocultas en el Excel.
    3. **Caché:** A veces Streamlit guarda el error. Intenta presionar la tecla **'C'** en tu teclado mientras ves la app para limpiar el caché.
    """)
