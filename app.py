import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 1. Configuración de página
st.set_page_config(page_title="Sistema Control PTAR", layout="wide", page_icon="💧")
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)
st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# --- CONFIGURACIÓN DE CONEXIÓN ---
# IMPORTANTE: Pega aquí la URL de la pestaña 'mantenimiento' (la que tiene el gid=XXXXX)
URL_DIRECTA_MANTO = "TU_URL_AQUI_CON_EL_GID" 

# 2. Función de limpieza de datos (Pestaña Vertimiento)
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
    
    # Carga Vertimiento (Hoja por defecto configurada en Secrets)
    df_raw = conn.read(ttl=0) 
    df_base = limpiar_datos_ptar(df_raw)

    # Carga Mantenimiento (Método GID para evitar Error 400)
    try:
        df_manto = conn.read(spreadsheet=URL_DIRECTA_MANTO, ttl=0)
        df_manto.columns = df_manto.columns.str.strip() # Limpiar espacios en nombres de columnas
    except:
        df_manto = pd.DataFrame()

    # --- BARRA LATERAL (LOGO Y FILTROS) ---
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
            m1, m2, m3, m4 = st.columns(4)
            avg_ph = df_filtrado['ph'].mean()
            avg_temp = df_filtrado['temp'].mean()
            avg_sst = df_filtrado['sst'].mean()

            m1.metric("Promedio pH", f"{avg_ph:.2f}", 
                      delta="EN NORMA" if 6.0 <= avg_ph <= 9.0 else "FUERA DE RANGO",
                      delta_color="normal" if 6.0 <= avg_ph <= 9.0 else "inverse")
            m2.metric("Temp Promedio", f"{avg_temp:.1f} °C",
                      delta="ESTABLE" if avg_temp <= 40 else "ELEVADA",
                      delta_color="normal" if avg_temp <= 40 else "inverse")
            m3.metric("SST Promedio", f"{avg_sst:.2f}",
                      delta="ÓPTIMO" if avg_sst <= 50 else "CRÍTICO",
                      delta_color="normal" if avg_sst <= 50 else "inverse")
            m4.metric("Total Registros", len(df_filtrado))

            st.subheader("📈 Análisis de pH")
            fig_t = px.line(df_filtrado.sort_values('fecha'), x='fecha', y='ph', markers=True)
            fig_t.add_hline(y=9.0, line_dash="dash", line_color="red")
            fig_t.add_hline(y=6.0, line_dash="dash", line_color="red")
            st.plotly_chart(fig_t, use_container_width=True)

            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("📊 Sólidos (SST)")
                df_s = df_filtrado.groupby('proceso')['sst'].mean().reset_index()
                fig_s = px.bar(df_s, x='proceso', y='sst', color='sst', title="SST por Etapa")
                st.plotly_chart(fig_s, use_container_width=True)
            with col_b:
                st.subheader("🌡️ Temperatura")
                df_temp_plot = df_filtrado.groupby('proceso')['temp'].mean().reset_index()
                fig_temp = px.line(df_temp_plot, x='proceso', y='temp', markers=True, title="Temperatura por Etapa")
                st.plotly_chart(fig_temp, use_container_width=True)
        else:
            st.warning("No hay datos para mostrar en Vertimientos.")

    with t2:
        st.info("Módulo de Agua Tratada en desarrollo.")

    with t3:
        st.subheader("🛠️ Panel de Control de Mantenimiento")
        
        if not df_manto.empty:
            # INDICADORES DE MANTENIMIENTO
            c1, c2, c3, c4 = st.columns(4)
            
            # Salud Promedio
            if 'SALUD' in df_manto.columns:
                df_manto['SALUD'] = pd.to_numeric(df_manto['SALUD'], errors='coerce')
                salud_val = df_manto['SALUD'].mean()
                c1.metric("Salud Promedio", f"{salud_val:.1f}/10", 
                          delta="SANA" if salud_val >= 7 else "CRÍTICA",
                          delta_color="normal" if salud_val >= 7 else "inverse")

            # Conteo de Estado Óptimo
            if 'ESTADO' in df_manto.columns:
                optimos = len(df_manto[df_manto['ESTADO'].str.upper() == 'OPTIMO'])
                c2.metric("Equipos Óptimos", f"{optimos}", f"de {len(df_manto)}")

            # Último Equipo intervenido
            if 'EQUIPO' in df_manto.columns:
                ultimo_eq = df_manto['EQUIPO'].iloc[-1]
                c3.metric("Última Draga/Equipo", ultimo_eq)

            c4.metric("Total Intervenciones", len(df_manto))

            st.markdown("---")

            # VISUALIZACIÓN
            col_tabla, col_grafica = st.columns([2, 1])
            with col_tabla:
                st.write("**Historial de Mantenimiento:**")
                st.dataframe(df_manto, use_container_width=True)
            
            with col_grafica:
                if 'EQUIPO' in df_manto.columns and 'SALUD' in df_manto.columns:
                    st.write("**Salud por Equipo:**")
                    fig_m = px.bar(df_manto, x='EQUIPO', y='SALUD', color='SALUD',
                                  color_continuous_scale='RdYlGn', range_color=[0, 10])
                    fig_m.update_layout(height=300, showlegend=False)
                    st.plotly_chart(fig_m, use_container_width=True)
        else:
            st.warning("No se encontraron registros de mantenimiento.")

except Exception as e:
    st.error(f"Error general: {e}")
