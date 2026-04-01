import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Configuración
st.set_page_config(page_title="Gestión Integral PTAR", layout="wide", page_icon="💧")

st.markdown('<p style="font-size:32px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# 2. Función de limpieza (Motor compartido)
def limpiar_datos(df, tipo="vertimiento"):
    df.columns = df.columns.str.strip()
    if tipo == "vertimiento":
        mapeo = {
            'Marca temporal': 'timestamp', 'Fecha del reporte': 'fecha', 
            'Proceso a reportar': 'proceso', 'ph': 'ph', 'Temperatura': 'temp', 
            'Solidos suspendidos': 'sst', 'Caudal del vertimiento': 'caudal'
        }
    else:
        # Aquí puedes definir mapeos para las otras hojas cuando las crees
        mapeo = {'Fecha': 'fecha', 'SST Salida': 'sst_salida', 'Equipo': 'equipo'}
    
    df = df.rename(columns=mapeo)
    
    # Conversión numérica
    for col in df.columns:
        if col in ['ph', 'temp', 'sst', 'caudal', 'sst_salida']:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha']).dt.date
    return df

# 3. Conexión Principal
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # --- CARGA DE DATOS POR PESTAÑA ---
    # Nota: El parámetro 'worksheet' debe coincidir con el nombre de la pestaña en tu Excel
    df_vertimiento = limpiar_datos(conn.read(worksheet="Vertimientos"), "vertimiento")
    
    # Intentamos leer las otras, si no existen aún, creamos DataFrames vacíos para que no falle
    try:
        df_tratada = limpiar_datos(conn.read(worksheet="Agua Tratada"), "tratada")
    except:
        df_tratada = pd.DataFrame()
        
    try:
        df_mantenimiento = conn.read(worksheet="Mantenimiento")
    except:
        df_mantenimiento = pd.DataFrame()

    # --- DISEÑO DE PESTAÑAS EN STREAMLIT ---
    tab1, tab2, tab3 = st.tabs(["📊 Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with tab1:
        st.subheader("Control de Parámetros de Entrada")
        # Aquí va toda la lógica de métricas y gráficas que ya teníamos
        col1, col2, col3 = st.columns(3)
        col1.metric("pH Promedio", f"{df_vertimiento['ph'].mean():.2f}")
        col2.metric("SST Promedio", f"{df_vertimiento['sst'].mean():.2f}")
        col3.metric("Total Reportes", len(df_vertimiento))
        
        st.line_chart(df_vertimiento.groupby('fecha')['ph'].mean())

    with tab2:
        st.subheader("Análisis de Salida y Eficiencia")
        if not df_tratada.empty:
            st.dataframe(df_tratada, use_container_width=True)
        else:
            st.info("Crea una pestaña llamada 'Agua Tratada' en tu Google Sheet para ver estos datos.")

    with tab3:
        st.subheader("Bitácora de Equipos")
        if not df_mantenimiento.empty:
            st.dataframe(df_mantenimiento, use_container_width=True)
        else:
            st.info("Crea una pestaña llamada 'Mantenimiento' en tu Google Sheet para el seguimiento de equipos.")

except Exception as e:
    st.error(f"Error al conectar: {e}")
    st.info("Asegúrate de que los nombres de las pestañas en el Excel coincidan con el código.")
