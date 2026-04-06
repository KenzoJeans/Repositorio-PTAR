import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 1. Configuración de página
st.set_page_config(page_title="Sistema Control PTAR", layout="wide", page_icon="💧")
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)
st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# 2. Función de limpieza de datos
def limpiar_datos_ptar(df):
    if df is None or df.empty:
        return pd.DataFrame()
    df.columns = df.columns.str.strip()
    mapeo = {
        'ph': 'ph', 'pH': 'ph', 'PH': 'ph',
        'temp': 'temp', 'Temperatura': 'temp',
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
    return df

# 3. Conexión Principal
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Intentamos leer las pestañas de forma independiente para que una no bloquee a la otra
    def cargar_hoja(nombre):
        try:
            # Intentamos leer la pestaña específica, si falla, leemos la principal
            return conn.read(worksheet=nombre, ttl=0)
        except:
            return conn.read(ttl=0) # Carga la primera hoja por defecto si el nombre falla

    # --- CUERPO PRINCIPAL ---
    t1, t2, t3 = st.tabs(["📊 Dashboard Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with t1:
        df_v = cargar_hoja("vertimiento")
        df_filtrado = limpiar_datos_ptar(df_v)
        
        if not df_filtrado.empty and 'ph' in df_filtrado.columns:
            m1, m2, m3, m4 = st.columns(4)
            avg_ph = df_filtrado['ph'].mean()
            status_ph = "normal" if 6.0 <= avg_ph <= 9.0 else "inverse"
            m1.metric("Promedio pH", f"{avg_ph:.2f}", delta="EN NORMA" if status_ph == "normal" else "FUERA", delta_color=status_ph)
            m4.metric("Total Registros", len(df_filtrado))
            
            st.subheader("📋 Detalle de Vertimientos")
            st.dataframe(df_filtrado, use_container_width=True)
        else:
            st.error("No se pudo cargar la pestaña 'vertimiento'. Revisa el nombre en Google Sheets.")

    with t3:
        st.subheader("🛠️ Estado de Maquinaria")
        df_m = cargar_hoja("mantenimiento")
        
        if not df_m.empty:
            df_m.columns = df_m.columns.str.strip().str.upper()
            st.write("### Historial de Mantenimiento")
            st.dataframe(df_m, use_container_width=True)
            
            if 'EQUIPO' in df_m.columns and 'SALUD' in df_m.columns:
                st.write("### ❤️ Salud de Equipos")
                # Mostrar los últimos estados
                df_resumen = df_m.drop_duplicates('EQUIPO', keep='last')
                cols = st.columns(len(df_resumen))
                for i, (_, row) in enumerate(df_resumen.iterrows()):
                    with cols[i]:
                        st.info(f"**{row['EQUIPO']}**\n\nSalud: {row['SALUD']}")
        else:
            st.error("No se pudo cargar la pestaña 'mantenimiento'.")

except Exception as e:
    st.error(f"Error de conexión: {e}. Revisa tus 'Secrets' en Streamlit.")
