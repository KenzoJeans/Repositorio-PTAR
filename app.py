import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 1. Configuración de página y Estilos Kenzo Jeans
st.set_page_config(page_title="Sistema Control PTAR", layout="wide", page_icon="💧")
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)
st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# 2. Función de limpieza de datos (Pestaña Vertimientos)
def limpiar_datos_ptar(df):
    if df is None or df.empty:
        return pd.DataFrame()
    
    df.columns = df.columns.str.strip()
    # Mapeo flexible para detectar columnas sin importar mayúsculas
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

# 3. Conexión y Lógica Principal
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # --- BARRA LATERAL ---
    try:
        st.sidebar.image("logo-white-kenzo.png", use_container_width=True)
    except:
        st.sidebar.warning("Logo no encontrado")

    st.sidebar.header("Filtros de Análisis")
    
    # --- CARGA DE DATOS (VERTIMIENTOS) ---
    df_raw = conn.read(worksheet="vertimiento", ttl=0) # Nombre según tu captura
    df_base = limpiar_datos_ptar(df_raw)

    # Filtros Dinámicos
    if not df_base.empty:
        min_f, max_f = min(df_base['fecha']), max(df_base['fecha'])
        rango = st.sidebar.date_input("Rango de fechas:", [min_f, max_f])
        
        lista_p = sorted(df_base['proceso'].unique().tolist())
        procesos_sel = st.sidebar.multiselect("Procesos:", lista_p, default=lista_p)
        
        df_filtrado = df_base[(df_base['proceso'].isin(procesos_sel))]
        if len(rango) == 2:
            df_filtrado = df_filtrado[(df_filtrado['fecha'] >= rango[0]) & (df_filtrado['fecha'] <= rango[1])]
            
        busqueda_q = st.sidebar.text_input("🔍 Buscar Químico:", "")
        if busqueda_q:
            df_filtrado = df_filtrado[df_filtrado['quimicos'].astype(str).str.contains(busqueda_q, case=False, na=False)]
    else:
        df_filtrado = pd.DataFrame()

    # --- TABS ---
    t1, t2, t3 = st.tabs(["📊 Dashboard Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with t1:
        if not df_filtrado.empty:
            m1, m2, m3, m4 = st.columns(4)
            avg_ph = df_filtrado['ph'].mean()
            avg_temp = df_filtrado['temp'].mean()
            
            m1.metric("Promedio pH", f"{avg_ph:.2f}", delta="EN NORMA" if 6<=avg_ph<=9 else "FUERA", delta_color="normal" if 6<=avg_ph<=9 else "inverse")
            m2.metric("Temp Promedio", f"{avg_temp:.1f} °C")
            m3.metric("SST Promedio", f"{df_filtrado['sst'].mean():.2f}")
            m4.metric("Registros", len(df_filtrado))

            fig_ph = px.line(df_filtrado.sort_values('fecha'), x='fecha', y='ph', markers=True, title="Tendencia de pH")
            fig_ph.add_hline(y=9.0, line_dash="dash", line_color="red")
            fig_ph.add_hline(y=6.0, line_dash="dash", line_color="red")
            st.plotly_chart(fig_ph, use_container_width=True)
            
            st.dataframe(df_filtrado, use_container_width=True)

    with t2:
        st.info("Módulo de Agua Tratada: Pendiente de vinculación con pestaña 'tratada'.")

    with t3:
        st.subheader("🛠️ Estado de Maquinaria")
        try:
            # Leer pestaña 'mantenimiento'
            df_m = conn.read(worksheet="mantenimiento", ttl=0)
            df_m.columns = df_m.columns.str.strip().str.upper()
            
            if not df_m.empty:
                # Obtener el reporte más reciente por equipo
                col_ts = 'MARCA TEMPORAL' if 'MARCA TEMPORAL' in df_m.columns else df_m.columns[0]
                df_m[col_ts] = pd.to_datetime(df_m[col_ts], errors='coerce')
                df_m = df_m.sort_values(by=col_ts, ascending=False)
                df_actual = df_m.drop_duplicates(subset=['EQUIPO'])
                
                # Tarjetas Visuales
                cols = st.columns(len(df_actual))
                for i, (_, row) in enumerate(df_actual.iterrows()):
                    with cols[i]:
                        salud = pd.to_numeric(str(row['SALUD']).replace('%',''), errors='coerce') or 0
                        color = "green" if salud > 70 else "orange" if salud > 40 else "red"
                        
                        st.markdown(f"""
                        <div style="border: 1px solid #444; padding: 15px; border-radius: 10px; background-color: #1e1e1e; text-align: center; min-height
