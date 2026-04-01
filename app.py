import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="Dashboard Planta de Tratamiento", layout="wide")

st.title("📊 Monitor de Parámetros de Vertimiento")
st.markdown("---")

# 1. Conexión a los datos
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Cambia 'spreadsheet' por el nombre de tu hoja si es distinto
    df_raw = conn.read()
    
    # 2. Función de limpieza y normalización
    def preparar_datos(df):
        # Limpieza de espacios invisibles en los nombres de las columnas
        df.columns = df.columns.str.strip()
        
        # Diccionario de mapeo basado en tu captura
        mapeo = {
            'Marca temporal': 'timestamp',
            'Fecha del reporte': 'fecha',
            'Hora del reporte': 'hora',
            'Proceso a reportar': 'proceso',
            'ph': 'ph',
            'Temperatura': 'temp',
            'Solidos suspendidos': 'sst',
            'Productos quimicos utilizados en el proceso': 'quimicos',
            'Caracteristicas visuales del vertimiento': 'visuales',
            'Caudal del vertimiento': 'caudal',
            'Suba aqui evidencia de la muestra tomada y e': 'evidencia'
        }
        
        # Renombramos y nos quedamos solo con las que nos sirven
        df = df.rename(columns=mapeo)
        
        # Convertir fecha a formato datetime para que Streamlit la entienda bien
        if 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha']).dt.date
            
        return df

    df = preparar_datos(df_raw)

    # 3. Interfaz del Dashboard
    st.sidebar.header("Filtros")
    proceso_sel = st.sidebar.multiselect(
        "Selecciona el Proceso:",
        options=df["proceso"].unique(),
        default=df["proceso"].unique()
    )

    df_filtrado = df[df["proceso"].isin(proceso_sel)]

    # 4. Métricas Rápidas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Promedio pH", round(df_filtrado["ph"].mean(), 2))
    with col2:
        st.metric("Promedio Temp (°C)", round(df_filtrado["temp"].mean(), 2))
    with col3:
        st.metric("Total Registros", len(df_filtrado))

    # 5. Visualización de la Tabla Limpia
    st.subheader("Datos Recientes")
    st.dataframe(df_filtrado, use_container_width=True)

    # 6. Gráfico simple de tendencia
    st.subheader("Tendencia de pH")
    st.line_chart(df_filtrado.set_index('fecha')['ph'])

except Exception as e:
    st.error(f"Error al conectar o procesar los datos: {e}")
    st.info("Revisa que el nombre de las columnas en el Excel coincida exactamente con el código.")
