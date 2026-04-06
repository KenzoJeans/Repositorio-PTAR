import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 1. Configuración de página
st.set_page_config(page_title="Sistema Control PTAR", layout="wide", page_icon="💧")

# --- ESTILOS ---
st.markdown("""
    <style>
    div.block-container {padding-top:2rem;}
    [data-testid="stMetricValue"] {font-size: 24px;}
    </style>
    """, unsafe_allow_html=True)

st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# 2. Funciones de Limpieza
def limpiar_datos(df):
    if df is None or df.empty: return pd.DataFrame()
    df.columns = df.columns.str.strip()
    return df

# 3. Conexión Principal (Con Limpieza de Cache Forzada)
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # --- BARRA LATERAL ---
    try:
        st.sidebar.image("logo-white-kenzo.png", use_container_width=True)
    except:
        pass
    
    st.sidebar.header("Filtros de Análisis")
    btn_refresh = st.sidebar.button("🔄 Forzar Actualización de Datos")
    
    # Usamos ttl=0 para que no guarde basura en el cache
    cache_time = 0 if btn_refresh else 300

    # --- TABS ---
    t1, t2, t3 = st.tabs(["📊 Dashboard Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with t1:
        try:
            # Lectura específica de la pestaña 'vertimiento'
            df_v = conn.read(worksheet="vertimiento", ttl=cache_time)
            df_v = limpiar_datos(df_v)
            
            if not df_v.empty:
                st.subheader("Análisis de Vertimientos")
                # Lógica de pH
                df_v['ph'] = pd.to_numeric(df_v.get('ph', 0), errors='coerce')
                st.metric("Promedio pH", f"{df_v['ph'].mean():.2f}")
                st.dataframe(df_v, use_container_width=True)
            else:
                st.warning("La pestaña 'vertimiento' existe pero no tiene datos.")
        except Exception as e:
            st.error(f"Error al leer pestaña 'vertimiento': {e}")

    with t3:
        st.subheader("🛠️ Estado de Maquinaria")
        try:
            # Lectura específica de la pestaña 'mantenimiento'
            df_m = conn.read(worksheet="mantenimiento", ttl=cache_time)
            df_m.columns = df_m.columns.str.strip().str.upper()
            
            if not df_m.empty:
                # Procesar datos de mantenimiento
                col_ts = 'MARCA TEMPORAL' if 'MARCA TEMPORAL' in df_m.columns else df_m.columns[0]
                df_m[col_ts] = pd.to_datetime(df_m[col_ts], errors='coerce')
                df_m = df_m.sort_values(by=col_ts, ascending=False)
                
                df_actual = df_m.drop_duplicates(subset=['EQUIPO'])
                
                cols = st.columns(len(df_actual) if len(df_actual) > 0 else 1)
                for i, (_, row) in enumerate(df_actual.iterrows()):
                    with cols[i]:
                        salud = pd.to_numeric(str(row.get('SALUD', '0')).replace('%',''), errors='coerce') or 0
                        color = "green" if salud > 70 else "orange" if salud > 40 else "red"
                        
                        st.markdown(f"""
                        <div style="border: 1px solid #444; padding: 15px; border-radius: 10px; background-color: #1e1e1e; text-align: center; min-height: 140px;">
                            <p style="margin: 0; font-weight: bold; color: white;">{row['EQUIPO']}</p>
                            <h2 style="color: {color};">{int(salud)}%</h2>
                        </div>
                        """, unsafe_allow_html=True)
                
                st.divider()
                st.dataframe(df_m, use_container_width=True)
            else:
                st.info("No hay datos en la pestaña 'mantenimiento'.")
                
        except Exception as e:
            st.error(f"Error al leer pestaña 'mantenimiento': {e}")

except Exception as e:
    st.error(f"Error General de Conexión: {e}")
