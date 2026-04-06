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
    
    return df.dropna(subset=['ph'])

# 3. Conexión y Carga de Datos (AJUSTADO PARA EVITAR ERROR 400)
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Intentar cargar vertimientos
    try:
        df_raw = conn.read(worksheet="vertimiento", ttl=0)
        df_base = limpiar_datos_ptar(df_raw)
    except Exception:
        st.error("Error al cargar la pestaña 'vertimiento'.")
        df_base = pd.DataFrame()

    # --- BARRA LATERAL (LOGO Y FILTROS) ---
    try:
        st.sidebar.image("logo-white-kenzo.png", use_container_width=True)
    except:
        st.sidebar.error("Error: No se encontró el logo.")

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

    if not df_filtrado.empty and 'quimicos' in df_filtrado.columns:
        busqueda_q = st.sidebar.text_input("🔍 Buscar Químico (escribe el nombre):", "")
        if busqueda_q:
            df_filtrado = df_filtrado[df_filtrado['quimicos'].astype(str).str.contains(busqueda_q, case=False, na=False)]

    # --- CUERPO PRINCIPAL ---
    t1, t2, t3 = st.tabs(["📊 Dashboard Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with t1:
        if not df_filtrado.empty:
            m1, m2, m3, m4 = st.columns(4)
            avg_ph = df_filtrado['ph'].mean()
            avg_temp = df_filtrado['temp'].mean()
            avg_sst = df_filtrado['sst'].mean()

            status_ph = "normal" if 6.0 <= avg_ph <= 9.0 else "inverse"
            m1.metric("Promedio pH", f"{avg_ph:.2f}", 
                      delta="EN NORMA" if status_ph == "normal" else "FUERA DE RANGO",
                      delta_color=status_ph)

            status_temp = "normal" if avg_temp <= 40 else "inverse"
            m2.metric("Temp Promedio", f"{avg_temp:.1f} °C",
                      delta="ESTABLE" if status_temp == "normal" else "ELEVADA",
                      delta_color=status_temp)

            status_sst = "normal" if avg_sst <= 50 else "inverse"
            m3.metric("SST Promedio", f"{avg_sst:.2f}",
                      delta="ÓPTIMO" if status_sst == "normal" else "CRÍTICO",
                      delta_color=status_sst)

            m4.metric("Total Registros", len(df_filtrado))

            st.subheader("📈 Análisis de pH")
            fig_t = px.line(df_filtrado.sort_values('fecha'), x='fecha', y='ph', markers=True)
            fig_t.add_hline(y=9.0, line_dash="dash", line_color="red")
            fig_t.add_hline(y=6.0, line_dash="dash", line_color="red")
            st.plotly_chart(fig_t, use_container_width=True)

            st.subheader("📋 Detalle de Datos")
            st.dataframe(df_filtrado, use_container_width=True)
        else:
            st.warning("No hay datos para los filtros seleccionados.")

    with t2:
        st.info("Módulo de Agua Tratada en desarrollo.")

    with t3:
        st.subheader("🛠️ Bitácora de Mantenimiento")
        try:
            # CARGA ESPECÍFICA PARA MANTENIMIENTO
            df_m = conn.read(worksheet="mantenimiento", ttl=0)
            if not df_m.empty:
                st.success("Datos de mantenimiento cargados.")
                st.dataframe(df_m, use_container_width=True)
            else:
                st.info("La pestaña 'mantenimiento' está vacía.")
        except Exception:
            st.error("Error al acceder a 'mantenimiento'. Verifique el nombre en el Excel.")

except Exception as e:
    st.error(f"Se detectó un error general: {e}")
