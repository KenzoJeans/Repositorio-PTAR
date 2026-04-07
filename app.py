import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 1. Configuración de página
st.set_page_config(page_title="Sistema Control PTAR", layout="wide", page_icon="💧")
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)
st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

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
    
    # CARGA DE PESTAÑA 1 (Vertimiento)
    df_raw = conn.read(worksheet="vertimiento", ttl=0) # Especificamos nombre para asegurar
    df_base = limpiar_datos_ptar(df_raw)

    # CARGA DE PESTAÑA 3 (Mantenimiento)
    # Si esta línea falla, revisa que el nombre en el Excel sea exactamente "mantenimiento"
    df_manto = conn.read(worksheet="mantenimiento", ttl=0)

    # --- BARRA LATERAL ---
    try:
        st.sidebar.image("logo-white-kenzo.png", use_container_width=True)
    except:
        st.sidebar.error("Error: No se encontró el logo.")

    st.sidebar.header("Filtros de Análisis")
    
    # Filtro de Fecha (Basado en Vertimiento)
    if not df_base.empty and 'fecha' in df_base.columns:
        min_f, max_f = min(df_base['fecha']), max(df_base['fecha'])
        rango_fechas = st.sidebar.date_input("Rango de fechas:", [min_f, max_f])
        if len(rango_fechas) == 2:
            df_base = df_base[(df_base['fecha'] >= rango_fechas[0]) & (df_base['fecha'] <= rango_fechas[1])]

    # Filtro de Proceso
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

            m1.metric("Promedio pH", f"{avg_ph:.2f}", delta="EN NORMA" if 6.0 <= avg_ph <= 9.0 else "FUERA DE RANGO")
            m2.metric("Temp Promedio", f"{avg_temp:.1f} °C")
            m3.metric("SST Promedio", f"{avg_sst:.2f}")
            m4.metric("Total Registros", len(df_filtrado))

            st.subheader("📈 Análisis de pH")
            fig_t = px.line(df_filtrado.sort_values('fecha'), x='fecha', y='ph', markers=True)
            st.plotly_chart(fig_t, use_container_width=True)
            
            st.subheader("📋 Detalle de Datos")
            st.dataframe(df_filtrado, use_container_width=True)
        else:
            st.warning("No hay datos para los filtros seleccionados.")

    with t2:
        st.info("Módulo de Agua Tratada en desarrollo.")

    with t3:
        st.subheader("🛠️ Registro de Actividades de Mantenimiento")
        if df_manto is not None and not df_manto.empty:
            st.write("A continuación se muestran los reportes de mantenimiento realizados:")
            st.dataframe(df_manto, use_container_width=True)
            
            # Un pequeño extra: Conteo por tipo de equipo/tarea si existe la columna
            if 'Equipo' in df_manto.columns:
                fig_manto = px.pie(df_manto, names='Equipo', title="Distribución de Mantenimiento por Equipo")
                st.plotly_chart(fig_manto, use_container_width=True)
        else:
            st.warning("No se encontraron datos en la pestaña de mantenimiento.")

except Exception as e:
    st.error(f"Se detectó un error: {e}")
