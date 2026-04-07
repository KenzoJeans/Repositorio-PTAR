import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 1. Configuración de página
st.set_page_config(page_title="Sistema Control PTAR", layout="wide", page_icon="💧")
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)
st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# --- CONFIGURACIÓN DE CONEXIÓN ---
# IMPORTANTE: Reemplaza con la URL de tu pestaña 'mantenimiento' que copiaste del navegador
URL_DIRECTA_MANTO = "TU_URL_AQUI_CON_EL_GID" 

# 2. Función de limpieza de datos (Pestaña Vertimiento - CODIGO BASE)
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
    
    return df.dropna(subset=['ph'])

# 3. Conexión y Carga de Datos
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Carga Vertimiento (Hoja principal de Secrets)
    df_raw = conn.read(ttl=0) 
    df_base = limpiar_datos_ptar(df_raw)

    # Carga Mantenimiento (URL Directa)
    try:
        df_manto = conn.read(spreadsheet=URL_DIRECTA_MANTO, ttl=0)
        df_manto.columns = df_manto.columns.str.strip()
    except:
        df_manto = pd.DataFrame()

    # --- BARRA LATERAL (FILTROS ORIGINALES) ---
    try:
        st.sidebar.image("logo-white-kenzo.png", use_container_width=True)
    except:
        pass

    st.sidebar.header("Filtros de Análisis")
    
    if not df_base.empty and 'fecha' in df_base.columns:
        min_f, max_f = min(df_base['fecha']), max(df_base['fecha'])
        rango_fechas = st.sidebar.date_input("Rango de fechas:", [min_f, max_f])
        if len(rango_fechas) == 2:
            df_base = df_base[(df_base['fecha'] >= rango_fechas[0]) & (df_base['fecha'] <= rango_fechas[1])]

    if not df_base.empty and 'proceso' in df_base.columns:
        lista_p = sorted(df_base['proceso'].unique().tolist())
        procesos_sel = st.sidebar.multiselect("Selecciona el Proceso:", lista_p, default=lista_p)
        df_filtrado = df_base[df_base['proceso'].isin(procesos_sel)]
    else:
        df_filtrado = df_base

    # --- CUERPO PRINCIPAL ---
    t1, t2, t3 = st.tabs(["📊 Dashboard Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with t1:
        if not df_filtrado.empty:
            # MÉTRICAS ORIGINALES
            m1, m2, m3, m4 = st.columns(4)
            avg_ph = df_filtrado['ph'].mean()
            avg_temp = df_filtrado['temp'].mean()
            avg_sst = df_filtrado['sst'].mean()

            m1.metric("Promedio pH", f"{avg_ph:.2f}", 
                      delta="EN NORMA" if 6.0 <= avg_ph <= 9.0 else "FUERA DE RANGO",
                      delta_color="normal" if 6.0 <= avg_ph <= 9.0 else "inverse")
            m2.metric("Temp Promedio", f"{avg_temp:.1f} °C",
                      delta="ESTABLE" if avg_temp <= 40 else "ELEVADA")
            m3.metric("SST Promedio", f"{avg_sst:.2f}",
                      delta="ÓPTIMO" if avg_sst <= 50 else "CRÍTICO")
            m4.metric("Total Registros", len(df_filtrado))

            # GRÁFICAS ORIGINALES
            st.subheader("📈 Análisis de pH")
            fig_t = px.line(df_filtrado.sort_values('fecha'), x='fecha', y='ph', markers=True)
            fig_t.add_hline(y=9.0, line_dash="dash", line_color="red")
            fig_t.add_hline(y=6.0, line_dash="dash", line_color="red")
            st.plotly_chart(fig_t, use_container_width=True)

            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("📊 Sólidos (SST)")
                df_s = df_filtrado.groupby('proceso')['sst'].mean().reset_index()
                fig_s = px.bar(df_s, x='proceso', y='sst', color='sst')
                st.plotly_chart(fig_s, use_container_width=True)
            with col_b:
                st.subheader("🌡️ Temperatura")
                df_temp_plot = df_filtrado.groupby('proceso')['temp'].mean().reset_index()
                fig_temp = px.line(df_temp_plot, x='proceso', y='temp', markers=True)
                st.plotly_chart(fig_temp, use_container_width=True)
            
            st.dataframe(df_filtrado, use_container_width=True)
        else:
            st.warning("No hay datos en Vertimientos.")

    with t2:
        st.info("Módulo en desarrollo.")

    with t3:
        st.subheader("🛠️ Panel de Mantenimiento por Equipo")
        
        if not df_manto.empty:
            # 1. Resumen General en Cards (Estilo Ayer)
            c1, c2, c3, c4 = st.columns(4)
            avg_salud = pd.to_numeric(df_manto['SALUD'], errors='coerce').mean()
            
            # Tarjeta Salud General con HTML para diseño "Card"
            st.markdown(f"""
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 20px;">
                    <div style="background-color: #1E1E1E; padding: 15px; border-radius: 10px; border-left: 5px solid #4CAF50;">
                        <small style="color: #888;">Salud Global</small><br>
                        <strong style="font-size: 20px;">{avg_salud:.1f}/10</strong>
                    </div>
                    <div style="background-color: #1E1E1E; padding: 15px; border-radius: 10px; border-left: 5px solid #2196F3;">
                        <small style="color: #888;">Equipos</small><br>
                        <strong style="font-size: 20px;">{len(df_manto['EQUIPO'].unique())}</strong>
                    </div>
                    <div style="background-color: #1E1E1E; padding: 15px; border-radius: 10px; border-left: 5px solid #FF9800;">
                        <small style="color: #888;">Último Operario</small><br>
                        <strong style="font-size: 16px;">{df_manto['Operario'].iloc[-1]}</strong>
                    </div>
                    <div style="background-color: #1E1E1E; padding: 15px; border-radius: 10px; border-left: 5px solid #9C27B0;">
                        <small style="color: #888;">Total Reportes</small><br>
                        <strong style="font-size: 20px;">{len(df_manto)}</strong>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # 2. SECCIÓN DE TARJETAS INDIVIDUALES (Lo nuevo que te gustó)
            st.markdown("### Estado de Equipos Registrados")
            equipos_unicos = df_manto['EQUIPO'].unique()
            columnas_equipos = st.columns(3) # Cuadrícula de 3

            for idx, eq_nombre in enumerate(equipos_unicos):
                # Obtener el último dato de ese equipo
                ultimo_dato = df_manto[df_manto['EQUIPO'] == eq_nombre].iloc[-1]
                salud_val = pd.to_numeric(ultimo_dato['SALUD'], errors='coerce')
                
                # Color según salud
                color_borde = "#4CAF50" if salud_val >= 8 else "#FFEB3B" if salud_val >= 6 else "#F44336"
                
                with columnas_equipos[idx % 3]:
                    st.markdown(f"""
                        <div style="background-color: #1E1E1E; padding: 15px; border-radius: 10px; border-top: 5px solid {color_borde}; margin-bottom: 15px; height: 180px;">
                            <h4 style="margin-bottom: 5px;">⚙️ {eq_nombre}</h4>
                            <p style="font-size: 14px; margin: 0; color: {color_borde};">Salud: <b>{salud_val}/10</b></p>
                            <p style="font-size: 12px; margin: 5px 0;">Estado: {ultimo_dato['ESTADO']}</p>
                            <hr style="margin: 10px 0; border: 0.5px solid #333;">
                            <p style="font-size: 11px; color: #888;"><b>Última tarea:</b><br>{ultimo_dato['QUE SE REALIZO'][:60]}...</p>
                            <p style="font-size: 10px; color: #555; text-align: right;">Prox: {ultimo_dato['FECHA PROX MANTENIMIENTO']}</p>
                        </div>
                    """, unsafe_allow_html=True)

            with st.expander("Ver tabla completa de mantenimiento"):
                st.dataframe(df_manto, use_container_width=True)

except Exception as e:
    st.error(f"Error detectado: {e}")
