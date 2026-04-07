import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 1. Configuración de página
st.set_page_config(page_title="Sistema Control PTAR", layout="wide", page_icon="💧")
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)
st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# --- CONFIGURACIÓN DE CONEXIÓN ---
# Pega aquí tu URL de la pestaña de mantenimiento (la del GID)
URL_DIRECTA_MANTO = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=746789412#gid=746789412" 

# 2. Función de limpieza de datos (Pestaña Vertimiento - BASE)
def limpiar_datos_ptar(df):
    if df is None or df.empty:
        return pd.DataFrame()
    df.columns = df.columns.str.strip()
    mapeo = {'ph': 'ph', 'pH': 'ph', 'temp': 'temp', 'sst': 'sst', 'Fecha del reporte': 'fecha', 'Proceso a reportar': 'proceso'}
    df = df.rename(columns={k: v for k, v in mapeo.items() if k in df.columns})
    for col in ['ph', 'temp', 'sst']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce').dt.date
    return df.dropna(subset=['ph'])

# 3. Conexión y Carga de Datos
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_base = limpiar_datos_ptar(conn.read(ttl=0))
    
    try:
        df_manto = conn.read(spreadsheet=URL_DIRECTA_MANTO, ttl=0)
        df_manto.columns = df_manto.columns.str.strip()
    except:
        df_manto = pd.DataFrame()

    # --- CUERPO PRINCIPAL ---
    t1, t2, t3 = st.tabs(["📊 Dashboard Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with t1:
        if not df_base.empty:
            st.metric("Total Registros Vertimientos", len(df_base))
            st.plotly_chart(px.line(df_base.sort_values('fecha'), x='fecha', y='ph', title="Histórico pH"), use_container_width=True)
            st.dataframe(df_base, use_container_width=True)
        else:
            st.warning("No hay datos en Vertimientos.")

    with t2:
        st.info("Módulo en desarrollo.")

    with t3:
        st.subheader("🛠️ Panel de Mantenimiento por Equipo")
        
        if not df_manto.empty:
            # Asegurar que SALUD sea número
            if 'SALUD' in df_manto.columns:
                df_manto['SALUD'] = pd.to_numeric(df_manto['SALUD'], errors='coerce').fillna(0)

            # 1. Resumen General (Cards de ayer)
            avg_s = df_manto['SALUD'].mean() if 'SALUD' in df_manto.columns else 0
            
            st.markdown(f"""
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 20px;">
                    <div style="background-color: #1E1E1E; padding: 15px; border-radius: 10px; border-left: 5px solid #4CAF50;">
                        <small style="color: #888;">Salud Global</small><br>
                        <strong style="font-size: 20px;">{avg_s:.1f}/10</strong>
                    </div>
                    <div style="background-color: #1E1E1E; padding: 15px; border-radius: 10px; border-left: 5px solid #2196F3;">
                        <small style="color: #888;">Equipos Registrados</small><br>
                        <strong style="font-size: 20px;">{len(df_manto['EQUIPO'].unique()) if 'EQUIPO' in df_manto.columns else 0}</strong>
                    </div>
                    <div style="background-color: #1E1E1E; padding: 15px; border-radius: 10px; border-left: 5px solid #9C27B0;">
                        <small style="color: #888;">Total Reportes</small><br>
                        <strong style="font-size: 20px;">{len(df_manto)}</strong>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # 2. SECCIÓN DE TARJETAS INDIVIDUALES
            if 'EQUIPO' in df_manto.columns:
                st.markdown("### Estado de Equipos")
                equipos_unicos = df_manto['EQUIPO'].unique()
                columnas_equipos = st.columns(3)

                for idx, eq_nombre in enumerate(equipos_unicos):
                    ultimo_dato = df_manto[df_manto['EQUIPO'] == eq_nombre].iloc[-1]
                    salud_val = ultimo_dato['SALUD']
                    color_b = "#4CAF50" if salud_val >= 8 else "#FFEB3B" if salud_val >= 6 else "#F44336"
                    
                    # Usamos 'Marca temporal' o 'Fecha' según lo que exista
                    fecha_val = ultimo_dato.get('Fecha', ultimo_dato.get('Marca temporal', 'N/A'))
                    prox_val = ultimo_dato.get('FECHA PROX MANTENIMIENTO', 'N/A')
                    tarea = ultimo_dato.get('QUE SE REALIZO', 'Sin descripción')

                    with columnas_equipos[idx % 3]:
                        st.markdown(f"""
                            <div style="background-color: #1E1E1E; padding: 15px; border-radius: 10px; border-top: 5px solid {color_b}; margin-bottom: 15px;">
                                <h4 style="margin-bottom: 5px;">⚙️ {eq_nombre}</h4>
                                <p style="font-size: 14px; margin: 0; color: {color_b};">Salud: <b>{salud_val}/10</b></p>
                                <p style="font-size: 11px; color: #888; margin-top: 5px;">Último: {fecha_val}</p>
                                <hr style="margin: 8px 0; border: 0.5px solid #333;">
                                <p style="font-size: 11px; height: 40px; overflow: hidden;">{tarea[:80]}...</p>
                                <p style="font-size: 10px; color: #555; text-align: right;">Próximo: {prox_val}</p>
                            </div>
                        """, unsafe_allow_html=True)
            
            st.markdown("---")
            st.write("**Historial Completo:**")
            st.dataframe(df_manto, use_container_width=True)
        else:
            st.warning("No se encontraron registros de mantenimiento.")

except Exception as e:
    st.error(f"Error detectado: {e}")
