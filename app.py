import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Sistema Control PTAR", layout="wide", page_icon="💧")

# Estilo para mejorar la interfaz
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)
st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# 2. FUNCIONES DE LIMPIEZA
def limpiar_datos_ptar(df):
    if df is None or df.empty:
        return pd.DataFrame()
    
    df.columns = df.columns.str.strip()
    # Mapeo flexible para las columnas de vertimiento
    mapeo = {
        'PH': 'ph', 'ph': 'ph',
        'TEMPERATURA': 'temp', 'temp': 'temp',
        'SOLIDOS SUSPENDIDOS': 'sst', 'sst': 'sst',
        'FECHA DEL REPORTE': 'fecha',
        'PROCESO A REPORTAR': 'proceso',
        'PRODUCTOS QUIMICOS UTILIZADOS EN EL PROCESO': 'quimicos'
    }
    df = df.rename(columns=mapeo)

    # Conversión numérica de parámetros
    for col in ['ph', 'temp', 'sst']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce').dt.date
    
    return df

# 3. CONEXIÓN PRINCIPAL
try:
    conn = st.connection("gsheets", type=GSheetsConnection)

    # BARRA LATERAL (Filtros generales)
    st.sidebar.header("Opciones de Visualización")

    # TABS (Pestañas de la App)
    t1, t2, t3 = st.tabs(["📊 Dashboard Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    # --- PESTAÑA 1: VERTIMIENTOS ---
    with t1:
        try:
            # Lectura de la pestaña exacta confirmada por el usuario
            df_v_raw = conn.read(worksheet="vertimiento", ttl=0)
            df_v = limpiar_datos_ptar(df_v_raw)

            if not df_v.empty:
                st.success("Datos de Vertimiento cargados correctamente.")
                
                # Columnas de métricas rápidas
                m1, m2, m3 = st.columns(3)
                m1.metric("Promedio pH", f"{df_v['ph'].mean():.2f}")
                m2.metric("Temp. Promedio", f"{df_v['temp'].mean():.1f} °C")
                m3.metric("SST Promedio", f"{df_v['sst'].mean():.1f}")

                # Gráfica de tendencia
                st.subheader("Evolución de Parámetros")
                fig = px.line(df_v.sort_values('fecha'), x='fecha', y='ph', color='proceso', markers=True)
                st.plotly_chart(fig, use_container_width=True)

                st.dataframe(df_v, use_container_width=True)
            else:
                st.warning("La pestaña 'vertimiento' existe pero parece estar vacía.")
        except Exception as e:
            st.error(f"Error al leer la pestaña 'vertimiento'. Revisa el nombre en el Excel.")

    # --- PESTAÑA 2: AGUA TRATADA ---
    with t2:
        try:
            df_t = conn.read(worksheet="tratada", ttl=0)
            if not df_t.empty:
                st.subheader("Registros de Agua Tratada")
                st.dataframe(df_t, use_container_width=True)
            else:
                st.info("Pestaña 'tratada' sin datos.")
        except:
            st.warning("No se pudo cargar la pestaña 'tratada'.")

    # --- PESTAÑA 3: MANTENIMIENTO ---
    with t3:
        st.subheader("🛠️ Bitácora de Mantenimiento de Equipos")
        try:
            # Lectura de la pestaña exacta confirmada por el usuario
            df_m = conn.read(worksheet="mantenimiento", ttl=0)
            
            if not df_m.empty:
                df_m.columns = df_m.columns.str.strip()
                
                # Visualización de Salud de Equipos
                if 'EQUIPO' in df_m.columns and 'SALUD' in df_m.columns:
                    df_resumen = df_m.drop_duplicates('EQUIPO', keep='last')
                    cols_equipos = st.columns(len(df_resumen))
                    
                    for i, (_, row) in enumerate(df_resumen.iterrows()):
                        with cols_equipos[i]:
                            st.metric(label=row['EQUIPO'], value=f"{row['SALUD']}", delta=row.get('ESTADO', ''))
                
                st.divider()
                st.write("### Historial de Intervenciones")
                st.dataframe(df_m, use_container_width=True)
            else:
                st.info("La pestaña de mantenimiento está lista pero no tiene registros aún.")
        except Exception as e:
            st.error("Error al leer la pestaña 'mantenimiento'. Verifica que el nombre sea idéntico en Google Sheets.")

except Exception as e:
    st.error(f"Error de conexión general: {e}")
