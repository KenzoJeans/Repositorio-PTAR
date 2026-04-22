import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import date

# 1. Configuración de página y Estilo
st.set_page_config(page_title="SGA - PTAR - Kenzo Jeans", layout="wide", page_icon="💧")

# --- ESTILOS PERSONALIZADOS ---
st.markdown("""
    <style>
        .block-container { padding-top: 1rem; padding-bottom: 0rem; }
        [data-testid="stImage"] img { object-fit: contain; }
        [data-testid="stSidebar"] { min-width: 320px; max-width: 350px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIÓN DE LIMPIEZA DE DATOS (CORREGIDA) ---
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
        'Proceso a reportar': 'proceso',
        'NOMBRE DEL QUÍMICO': 'quimico',
        'NOMBRE DEL QUIMICO': 'quimico'
    }
    
    df = df.rename(columns=mapeo)

    # Conversión numérica
    columnas_num = ['ph', 'temp', 'sst', 'cond', 'caudal', 'CANTIDAD']
    for col in columnas_num:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
    
    # NORMALIZACIÓN DE FECHAS (Crucial para los filtros)
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce').dt.date
    elif 'fecha_h' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha_h'], errors='coerce').dt.date
    
    return df.dropna(subset=['fecha']) if 'fecha' in df.columns else df

# --- CARGA DE DATOS PRINCIPAL ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Definición de URLs
    URL_DIRECTA_MANTO = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=746789412#gid=746789412"
    URL_DIRECTA_TRATADA = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=1338797542#gid=1338797542"
    URL_DIRECTA_QUIMICOS = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=170562532#gid=170562532"

    # Lectura y Limpieza
    df_base_full = limpiar_datos_ptar(conn.read(ttl=0))
    
    try:
        df_tratada = limpiar_datos_ptar(conn.read(spreadsheet=URL_DIRECTA_TRATADA, ttl=0))
    except:
        df_tratada = pd.DataFrame()

    try:
        df_manto = conn.read(spreadsheet=URL_DIRECTA_MANTO, ttl=0)
        df_manto.columns = df_manto.columns.str.strip().str.upper()
    except:
        df_manto = pd.DataFrame()

    try:
        df_kardex = conn.read(spreadsheet=URL_DIRECTA_QUIMICOS, ttl=0)
    except:
        df_kardex = pd.DataFrame()

    # --- BARRA LATERAL Y FILTROS ---
    with st.sidebar:
        try:
            st.image("logo-white-kenzo.png", use_container_width=True)
        except:
            st.title("KENZO JEANS")
        
        st.header("🔍 Filtros Dashboard")
        df_vert_filtrado = df_base_full.copy()

        # 1. Filtro de Procesos
        if 'proceso' in df_vert_filtrado.columns:
            procesos = sorted(df_vert_filtrado['proceso'].unique().tolist())
            sel = st.multiselect("Seleccionar Procesos:", procesos, default=procesos)
            df_vert_filtrado = df_vert_filtrado[df_vert_filtrado['proceso'].isin(sel)]

        # 2. Filtro de Químicos (Búsqueda textual)
        filtro_q = st.text_input("Filtrar por Químico:", "")
        if filtro_q and 'quimico' in df_vert_filtrado.columns:
            df_vert_filtrado = df_vert_filtrado[df_vert_filtrado['quimico'].astype(str).str.contains(filtro_q, case=False, na=False)]

        # 3. FILTRO DE FECHAS (CORREGIDO)
        if not df_base_full.empty and 'fecha' in df_base_full.columns:
            st.subheader("📅 Rango de Tiempo")
            min_f, max_f = min(df_base_full['fecha']), max(df_base_full['fecha'])
            rango = st.date_input("Seleccionar fechas:", [min_f, max_f], min_value=min_f, max_value=max_f)
            
            if isinstance(rango, (list, tuple)) and len(rango) == 2:
                df_vert_filtrado = df_vert_filtrado[(df_vert_filtrado['fecha'] >= rango[0]) & (df_vert_filtrado['fecha'] <= rango[1])]

    # --- PESTAÑAS ---
    t1, t2, t3, t4 = st.tabs(["📊 Dashboard de vertimientos", "🧪 Agua tratada", "🛠️ Mantenimiento", "🧪 Consumo de químicos"])

    with t1:
        if not df_vert_filtrado.empty:
            # Asegurar orden para gráficas coherentes
            df_vert_plot = df_vert_filtrado.sort_values('fecha')

            m1, m2, m3, m4 = st.columns(4)
            avg_ph = df_vert_plot['ph'].mean()
            avg_temp = df_vert_plot['temp'].mean()
            avg_sst = df_vert_plot['sst'].mean()
            
            m1.metric("Promedio pH", f"{avg_ph:.2f}", delta="NORMA" if 6<=avg_ph<=9 else "ALERTA", delta_color="normal" if 6<=avg_ph<=9 else "inverse")
            m2.metric("Temp Promedio", f"{avg_temp:.1f} °C", delta="NORMAL" if avg_temp<=40 else "ALTA", delta_color="normal" if avg_temp<=40 else "inverse")
            m3.metric("SST Promedio", f"{avg_sst:.1f} mg/L")
            m4.metric("Registros", len(df_vert_plot))

            st.markdown("---")

            col1, col2 = st.columns(2)
            with col1:
                st.write("**📈 Histórico de pH (Tendencia Real)**")
                st.plotly_chart(px.line(df_vert_plot, x='fecha', y='ph', markers=True, template="plotly_dark"), use_container_width=True)
            with col2:
                st.write("**📊 pH por proceso**")
                df_ph_p = df_vert_plot.groupby('proceso')['ph'].mean().reset_index()
                st.plotly_chart(px.bar(df_ph_p, x='proceso', y='ph', color='proceso', template="plotly_dark"), use_container_width=True)

            col3, col4 = st.columns(2)
            with col3:
                st.markdown("<h4 style='text-align: center; color: #FFA726;'>🌡️ Tendencia de temperatura</h4>", unsafe_allow_html=True)
                fig_temp = px.area(df_vert_plot, x='fecha', y='temp', template="plotly_dark", color_discrete_sequence=['#FF9800'])
                st.plotly_chart(fig_temp, use_container_width=True)
            with col4:
                st.markdown("<h4 style='text-align: center; color: #FFD54F;'>📊 Temperatura por proceso</h4>", unsafe_allow_html=True)
                df_temp_proc = df_vert_plot.groupby('proceso')['temp'].mean().reset_index()
                st.plotly_chart(px.line(df_temp_proc, x='proceso', y='temp', markers=True, template="plotly_dark", color_discrete_sequence=['#FFD54F']), use_container_width=True)

            st.write("**📄 Tabla de Datos Filtrados**")
            st.dataframe(df_vert_plot, use_container_width=True)
        else:
            st.warning("Ajusta los filtros para ver datos.")

    with t2:
        if not df_tratada.empty:
            # Sincronizar filtro de fecha con pestaña 2
            df_t_filtrada = df_tratada.copy()
            if isinstance(rango, (list, tuple)) and len(rango) == 2:
                df_t_filtrada = df_t_filtrada[(df_t_filtrada['fecha'] >= rango[0]) & (df_t_filtrada['fecha'] <= rango[1])]
            
            df_t_plot = df_t_filtrada.sort_values('fecha')
            
            # KPIs Eficiencia
            sst_sal = df_t_plot['sst'].mean()
            sst_ent = df_base_full['sst'].mean() if not df_base_full.empty else 1
            remocion = max(0, (1 - (sst_sal / sst_ent)) * 100) if sst_ent > 0 else 0

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("SST Salida", f"{sst_sal:.1f} mg/L", delta=f"{remocion:.1f}% Eficiencia")
            c2.metric("pH Salida", f"{df_t_plot['ph'].mean():.2f}")
            c3.metric("Temp Salida", f"{df_t_plot['temp'].mean():.1f} °C")
            c4.metric("Caudal Total", f"{df_t_plot['caudal'].sum():.1f} m³")

            st.plotly_chart(px.line(df_t_plot, x='fecha', y='ph', title="pH Agua Tratada", markers=True, color_discrete_sequence=['#00C853'], template="plotly_dark"), use_container_width=True)
        else:
            st.warning("No hay datos en 'Agua Tratada'.")

    with t3:
        st.subheader("🛠️ Estado de Equipos")
        if not df_manto.empty:
            if 'SALUD' in df_manto.columns:
                df_manto['SALUD'] = pd.to_numeric(df_manto['SALUD'], errors='coerce').fillna(0)
            
            # Mostrar tarjetas de equipos... (Lógica de tu código original)
            equipos = df_manto['EQUIPO'].unique() if 'EQUIPO' in df_manto.columns else []
            cols_eq = st.columns(len(equipos) if 0 < len(equipos) <= 3 else 3)
            # [Aquí continúa tu lógica de tarjetas y Heatmap...]
            st.info("Visualización de mantenimiento activa.")
            st.dataframe(df_manto, use_container_width=True)

    with t4:
        st.subheader("📦 Gestión de Inventarios")
        if not df_kardex.empty:
            # Lógica de inventarios (Sulfato, Cal, Polímero)
            # [Aquí continúa tu lógica de STOCK_INICIAL y KPIs de Kardex...]
            st.dataframe(df_kardex, use_container_width=True)

except Exception as e:
    st.error(f"Error crítico en la aplicación: {e}")
