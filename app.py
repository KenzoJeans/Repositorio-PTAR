import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 1. Configuración de página
st.set_page_config(page_title="Sistema Control PTAR", layout="wide", page_icon="💧")
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)
st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# --- CONFIGURACIÓN DE CONEXIÓN ---
# Pega aquí la URL de tu pestaña 'mantenimiento' (la que tiene el gid=XXXXX)
URL_DIRECTA_MANTO = "TU_URL_AQUI_CON_EL_GID" 

# 2. Función de limpieza de datos (Pestaña Vertimiento)
def limpiar_datos_ptar(df):
    if df is None or df.empty: return pd.DataFrame()
    df.columns = df.columns.str.strip()
    mapeo = {'ph': 'ph', 'pH': 'ph', 'temp': 'temp', 'sst': 'sst', 'Fecha del reporte': 'fecha', 'Proceso a reportar': 'proceso'}
    df = df.rename(columns={k: v for k, v in mapeo.items() if k in df.columns})
    for col in ['ph', 'temp', 'sst']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce').dt.date
    return df.dropna(subset=['ph'])

# 3. Conexión y Carga
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_base = limpiar_datos_ptar(conn.read(ttl=0))
    try:
        df_manto = conn.read(spreadsheet=URL_DIRECTA_MANTO, ttl=0)
        df_manto.columns = df_manto.columns.str.strip()
    except:
        df_manto = pd.DataFrame()

    # --- BARRA LATERAL ---
    try: st.sidebar.image("logo-white-kenzo.png", use_container_width=True)
    except: pass

    # --- CUERPO PRINCIPAL ---
    t1, t2, t3 = st.tabs(["📊 Dashboard Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with t1:
        if not df_base.empty:
            m1, m2, m3 = st.columns(3)
            m1.metric("Promedio pH", f"{df_base['ph'].mean():.2f}")
            m2.metric("Temp Máxima", f"{df_base['temp'].max():.1f} °C")
            m3.metric("Total Reportes", len(df_base))
            st.plotly_chart(px.line(df_base.sort_values('fecha'), x='fecha', y='ph', title="Histórico pH"), use_container_width=True)
        else:
            st.warning("No hay datos en Vertimientos.")

    with t2:
        st.info("Módulo en desarrollo.")

    with t3:
        st.subheader("🛠️ Estado Individual por Equipo")
        
        if not df_manto.empty:
            # 1. RESUMEN GENERAL (TARJETAS SUPERIORES)
            st.markdown("### Resumen del Sistema")
            cols_resumen = st.columns(4)
            avg_salud_gen = pd.to_numeric(df_manto['SALUD'], errors='coerce').mean()
            cols_resumen[0].metric("Salud Global", f"{avg_salud_gen:.1f}/10")
            cols_resumen[1].metric("Equipos Activos", len(df_manto['EQUIPO'].unique()))
            cols_resumen[2].metric("Total Mantos", len(df_manto))
            cols_resumen[3].metric("Última Fecha", str(df_manto['Fecha'].iloc[-1]))
            
            st.markdown("---")
            
            # 2. TARJETAS INDIVIDUALES POR EQUIPO
            st.markdown("### Fichas de Equipos Registrados")
            # Creamos una cuadrícula de 3 columnas para las tarjetas de los equipos
            equipos = df_manto['EQUIPO'].unique()
            cols_cards = st.columns(3)
            
            for i, equipo in enumerate(equipos):
                # Obtenemos el último registro de este equipo específico
                datos_eq = df_manto[df_manto['EQUIPO'] == equipo].iloc[-1]
                salud = pd.to_numeric(datos_eq['SALUD'], errors='coerce')
                color = "#4CAF50" if salud >= 8 else "#FFEB3B" if salud >= 6 else "#F44336"
                
                with cols_cards[i % 3]:
                    st.markdown(f"""
                        <div style="background-color: #1E1E1E; padding: 15px; border-radius: 10px; border-top: 4px solid {color}; margin-bottom: 20px;">
                            <h4 style="margin: 0; color: white;">⚙️ {equipo}</h4>
                            <p style="margin: 5px 0; font-size: 13px; color: #BBB;">Estado: <b>{datos_eq['ESTADO']}</b></p>
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-size: 20px; font-weight: bold; color: {color};">{salud}/10</span>
                                <span style="font-size: 11px; color: #888;">Prox: {datos_eq['FECHA PROX MANTENIMIENTO']}</span>
                            </div>
                            <p style="margin-top: 10px; font-size: 12px; font-style: italic; color: #999;">
                                Ult. tarea: {datos_eq['QUE SE REALIZO'][:40]}...
                            </p>
                        </div>
                    """, unsafe_allow_html=True)

            # 3. TABLA DETALLADA AL FINAL
            with st.expander("Ver historial completo de mantenimiento"):
                st.dataframe(df_manto, use_container_width=True)
        else:
            st.warning("No hay registros en mantenimiento.")

except Exception as e:
    st.error(f"Error: {e}")
