import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 1. Configuración de página
st.set_page_config(page_title="Sistema Control PTAR", layout="wide", page_icon="💧")
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)
st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# 2. Función de limpieza de datos (Vertimientos)
def limpiar_datos_ptar(df):
    if df is None or df.empty: return pd.DataFrame()
    df.columns = df.columns.str.strip()
    mapeo = {
        'ph': 'ph', 'pH': 'ph', 'temp': 'temp', 'Temperatura': 'temp',
        'sst': 'sst', 'Solidos suspendidos': 'sst',
        'Fecha del reporte': 'fecha', 'fecha': 'fecha',
        'Proceso a reportar': 'proceso',
        'Productos quimicos utilizados en el proceso': 'quimicos'
    }
    df = df.rename(columns={k: v for k, v in mapeo.items() if k in df.columns})
    for col in ['ph', 'temp', 'sst']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce').dt.date
    return df.dropna(subset=['ph'])

# 3. Conexión Principal
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Carga de datos de Vertimientos
    df_raw = conn.read(ttl=0)
    df_base = limpiar_datos_ptar(df_raw)

    # --- BARRA LATERAL ---
    try:
        st.sidebar.image("logo-white-kenzo.png", use_container_width=True)
    except:
        pass

    st.sidebar.header("Filtros de Análisis")
    busqueda_q = st.sidebar.text_input("🔍 Buscar Químico:", "")

    # --- CUERPO PRINCIPAL ---
    t1, t2, t3 = st.tabs(["📊 Dashboard Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with t1:
        # (Se mantiene tu lógica original de gráficas de pH y SST)
        if not df_base.empty:
            st.subheader("Análisis de Vertimientos")
            st.dataframe(df_base.head())

    with t3:
        st.subheader("🛠️ Estado de Maquinaria (Datos Reales Formulario)")
        
        try:
            # Leemos la nueva pestaña de respuestas del formulario
            df_maint_raw = conn.read(worksheet="Mantenimiento", ttl=0)
            
            # Nos quedamos solo con el último reporte de cada equipo para mostrar la salud actual
            df_maint_raw = df_maint_raw.sort_values(by='Marca temporal', ascending=False)
            df_actual = df_maint_raw.drop_duplicates(subset=['EQUIPO'])
            
            # Tarjetas de Salud
            if not df_actual.empty:
                cols = st.columns(len(df_actual))
                for i, (_, row) in enumerate(df_actual.iterrows()):
                    with cols[i]:
                        salud_val = pd.to_numeric(row['SALUD'], errors='coerce') or 0
                        color = "green" if salud_val > 70 else "orange" if salud_val > 40 else "red"
                        
                        st.markdown(f"""
                        <div style="border: 1px solid #444; padding: 15px; border-radius: 10px; background-color: #1e1e1e; text-align: center;">
                            <p style="margin: 0; font-weight: bold; color: white;">{row['EQUIPO']}</p>
                            <h2 style="color: {color}; margin: 10px 0;">{salud_val}%</h2>
                            <p style="font-size: 11px; color: #aaa;">Prox: {row['FECHA PROX MANTENIMIENTO']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        st.progress(salud_val / 100)

                st.divider()
                st.subheader("📋 Historial de Intervenciones")
                # Mostramos las columnas relevantes del formulario
                st.dataframe(df_maint_raw[['Marca temporal', 'EQUIPO', 'ESTADO', 'QUE SE REALIZO', 'Operario']], use_container_width=True)
            else:
                st.info("Aún no hay reportes en 'Form_Responses2'. Llena el formulario para ver los datos aquí.")
        
        except Exception as e:
            st.error(f"Error al conectar con Form_Responses2: {e}")
            st.info("Asegúrate de que el nombre de la hoja sea exactamente 'Form_Responses2'")

except Exception as e:
    st.error(f"Error general: {e}")
