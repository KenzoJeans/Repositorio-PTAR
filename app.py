import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 1. Configuración de página y Estilo
st.set_page_config(page_title="SGA - PTAR - Kenzo Jeans", layout="wide", page_icon="💧")
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)

# --- ENCABEZADO PERSONALIZADO KENZO JEANS SAS ---
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
        }
        [data-testid="stImage"] img {
            object-fit: contain;
        }
    </style>
    """, unsafe_allow_html=True)

col_logo, col_titulo = st.columns([1.2, 5])

with col_logo:
    try:
        st.image("logo-white-kenzo.png", use_container_width=True)
    except Exception:
        st.markdown("**KENZO JEANS**")

with col_titulo:
    st.title("SGA - Gestión Integral PTAR - Kenzo Jeans SAS")

# --- CONFIGURACIÓN DE CONEXIÓN ---
URL_DIRECTA_MANTO = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=746789412#gid=746789412"
URL_DIRECTA_TRATADA = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=1338797542#gid=1338797542"
URL_DIRECTA_QUIMICOS = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=170562532#gid=170562532"

# 2. Función de limpieza de datos UNIFICADA (CON CORRECCIÓN DE FECHA)
def limpiar_datos_ptar(df):
    if df is None or df.empty:
        return pd.DataFrame()
    
    df.columns = df.columns.str.strip()
    df = df.loc[:, ~df.columns.duplicated()]
    
    mapeo = {
        'ph': 'ph', 'pH': 'ph', 'PH': 'ph', 'pH Tratada': 'ph',
        'temp': 'temp', 'Temperatura': 'temp', 'Temperatura Tratada': 'temp',
        'sst': 'sst', 'SST': 'sst', 'SST Tratada': 'sst', 'Solidos suspendidos': 'sst',
        'Conductividad Tratada': 'cond', 'Caudal tratado': 'caudal',
        'Fecha': 'fecha', 'fecha': 'fecha', 'Fecha del reporte': 'fecha', 
        'Marca temporal': 'fecha_h',
        'Proceso a reportar': 'proceso'
    }
    
    nuevos_nombres = {}
    for col in df.columns:
        if col in mapeo:
            target = mapeo[col]
            if target not in nuevos_nombres.values():
                nuevos_nombres[col] = target
    
    df = df.rename(columns=nuevos_nombres)

    columnas_num = ['ph', 'temp', 'sst', 'cond', 'caudal']
    for col in columnas_num:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        else:
            df[col] = 0.0
    
    # AJUSTE CRÍTICO PARA EL FILTRO: Asegurar formato datetime
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
    elif 'fecha_h' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha_h'], errors='coerce')
    
    return df.dropna(subset=['fecha'])

# 3. Carga de Datos Principal
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_raw = conn.read(ttl=0) 
    df_base_full = limpiar_datos_ptar(df_raw)

    try:
        df_tratada = limpiar_datos_ptar(conn.read(spreadsheet=URL_DIRECTA_TRATADA, ttl=0))
    except:
        df_tratada = pd.DataFrame()

    try:
        df_manto = conn.read(spreadsheet=URL_DIRECTA_MANTO, ttl=0)
        df_manto.columns = df_manto.columns.str.strip()
    except:
        df_manto = pd.DataFrame()

    try:
        df_kardex = conn.read(spreadsheet=URL_DIRECTA_QUIMICOS, ttl=0)
    except:
        df_kardex = pd.DataFrame()

    # --- BARRA LATERAL (FILTROS CONECTADOS) ---
    with st.sidebar:
        st.header("🔍 Filtros Dashboard")
        
        # Esta es la variable que alimentará a T1 y T2
        df_filtrado = df_base_full.copy()

        if not df_base_full.empty and 'proceso' in df_base_full.columns:
            procesos = sorted(df_base_full['proceso'].unique().tolist())
            sel = st.multiselect("Seleccionar Procesos:", procesos, default=procesos)
            df_filtrado = df_filtrado[df_filtrado['proceso'].isin(sel)]

        st.markdown("---")
        
        # FILTRO DE FECHAS: Ahora sí afecta a df_filtrado
        if not df_base_full.empty and 'fecha' in df_base_full.columns:
            st.subheader("📅 Rango de Tiempo")
            min_f, max_f = df_base_full['fecha'].min(), df_base_full['fecha'].max()
            rango = st.date_input("Seleccionar fechas:", [min_f, max_f])
            
            if isinstance(rango, list) and len(rango) == 2:
                start_date = pd.to_datetime(rango[0])
                end_date = pd.to_datetime(rango[1])
                df_filtrado = df_filtrado[(df_filtrado['fecha'] >= start_date) & (df_filtrado['fecha'] <= end_date)]

    # --- PESTAÑAS ---
    t1, t2, t3, t4 = st.tabs(["📊 Dashboard de vertimientos", "🧪 Agua tratada", "🛠️ Mantenimiento", "🧪 Consumo de químicos"])

    with t1:
        # Usamos df_filtrado para que todo reaccione al calendario
        if not df_filtrado.empty:
            m1, m2, m3, m4 = st.columns(4)
            avg_ph = df_filtrado['ph'].mean()
            avg_temp = df_filtrado['temp'].mean()
            avg_sst = df_filtrado['sst'].mean()
            
            m1.metric("Promedio pH", f"{avg_ph:.2f}", delta="NORMA" if 6<=avg_ph<=9 else "ALERTA", delta_color="normal" if 6<=avg_ph<=9 else "inverse")
            m2.metric("Temp Promedio", f"{avg_temp:.1f} °C", delta="NORMAL" if avg_temp<=40 else "ALTA", delta_color="normal" if avg_temp<=40 else "inverse")
            m3.metric("SST Promedio", f"{avg_sst:.1f} mg/L")
            m4.metric("Registros", len(df_filtrado))

            st.markdown("---")

            col1, col2 = st.columns(2)
            with col1:
                st.write("**📈 Histórico de pH (Tintorería)**")
                fig_ph = px.line(df_filtrado.sort_values('fecha'), x='fecha', y='ph', markers=True, template="plotly_dark")
                fig_ph.update_xaxes(type='date')
                st.plotly_chart(fig_ph, use_container_width=True)
            with col2:
                st.write("**📊 pH por proceso**")
                df_ph_p = df_filtrado.groupby('proceso')['ph'].mean().reset_index()
                st.plotly_chart(px.bar(df_ph_p, x='proceso', y='ph', color='proceso', template="plotly_dark"), use_container_width=True)

            col3, col4 = st.columns(2)
            with col3:
                st.markdown("<h4 style='text-align: center; color: #FFA726;'>🌡️ Tendencia de temperatura</h4>", unsafe_allow_html=True)
                fig_temp = px.area(df_filtrado.sort_values('fecha'), x='fecha', y='temp', template="plotly_dark", color_discrete_sequence=['#FF9800'])
                fig_temp.update_xaxes(type='date')
                st.plotly_chart(fig_temp, use_container_width=True)
            with col4:
                st.markdown("<h4 style='text-align: center; color: #FFD54F;'>📊 Temperatura por proceso</h4>", unsafe_allow_html=True)
                df_temp_proc = df_filtrado.groupby('proceso')['temp'].mean().reset_index()
                st.plotly_chart(px.line(df_temp_proc, x='proceso', y='temp', markers=True, template="plotly_dark"), use_container_width=True)
            
            st.write("**📄 Tabla de Datos Filtrados**")
            st.dataframe(df_filtrado, use_container_width=True)
        else:
            st.warning("No hay datos para el rango seleccionado.")

    with t2:
        # También conectamos Agua Tratada al filtro de fecha principal
        if not df_tratada.empty:
            # Sincronizamos df_tratada con las fechas del sidebar
            if isinstance(rango, list) and len(rango) == 2:
                df_trat_f = df_tratada[(df_tratada['fecha'] >= pd.to_datetime(rango[0])) & (df_tratada['fecha'] <= pd.to_datetime(rango[1]))]
            else:
                df_trat_f = df_tratada

            if not df_trat_f.empty:
                st.subheader("🧪 Monitoreo de Agua Tratada")
                st.plotly_chart(px.line(df_trat_f.sort_values('fecha'), x='fecha', y='ph', title="pH Salida", template="plotly_dark", color_discrete_sequence=['#00C853']), use_container_width=True)
            else:
                st.info("No hay datos de agua tratada en estas fechas.")

    with t3:
        st.subheader("🛠️ Mantenimiento de Equipos")
        if not df_manto.empty:
            st.dataframe(df_manto, use_container_width=True)

    with t4:
        st.subheader("🧪 Consumo de Químicos")
        if not df_kardex.empty:
            st.dataframe(df_kardex, use_container_width=True)

except Exception as e:
    st.error(f"Error detectado: {e}")
