import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Configuración de la página
st.set_page_config(page_title="Dashboard PTAR Pro", layout="wide", page_icon="💧")

st.markdown("""
    <style>
    .main-title { font-size:32px !important; font-weight: bold; color: #1E88E5; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<p class="main-title">🌊 Control de Vertimientos - Planta de Tratamiento</p>', unsafe_allow_html=True)

# 2. Motor de datos
def preparar_datos(df):
    df.columns = df.columns.str.strip()
    mapeo = {
        'Marca temporal': 'timestamp', 'Fecha del reporte': 'fecha', 
        'Hora del reporte': 'hora', 'Proceso a reportar': 'proceso',
        'ph': 'ph', 'Temperatura': 'temp', 'Solidos suspendidos': 'sst',
        'Productos quimicos utilizados en el proceso': 'quimicos',
        'Caudal del vertimiento': 'caudal'
    }
    df = df.rename(columns=mapeo)
    
    cols_numericas = ['ph', 'temp', 'sst', 'caudal']
    for col in cols_numericas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha']).dt.date
    
    return df.dropna(subset=['ph'])

# 3. Lógica Principal
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_raw = conn.read()
    df = preparar_datos(df_raw)

    # --- SIDEBAR MEJORADA ---
    st.sidebar.header("🔍 Control de Filtros")
    
    # Filtro de Procesos
    procesos = df["proceso"].unique().tolist()
    proceso_sel = st.sidebar.multiselect("Procesos:", procesos, default=procesos)
    
    # Filtro de Químicos (NUEVO)
    busqueda_quimico = st.sidebar.text_input("Buscar por Insumo/Químico:", "")
    
    # Filtro de Fechas
    f_min, f_max = df["fecha"].min(), df["fecha"].max()
    rango_fecha = st.sidebar.date_input("Rango de fechas:", [f_min, f_max])

    # Aplicar filtros
    df_filtrado = df[df["proceso"].isin(proceso_sel)]
    if busqueda_quimico:
        df_filtrado = df_filtrado[df_filtrado['quimicos'].str.contains(busqueda_quimico, case=False, na=False)]
    if len(rango_fecha) == 2:
        df_filtrado = df_filtrado[(df_filtrado["fecha"] >= rango_fecha[0]) & (df_filtrado["fecha"] <= rango_fecha[1])]

    # --- MÉTRICAS CON SEMÁFORO (NUEVO) ---
    col1, col2, col3, col4 = st.columns(4)
    
    prom_ph = df_filtrado['ph'].mean()
    prom_temp = df_filtrado['temp'].mean()
    
    with col1:
        # Delta muestra si el pH es ideal (6-9)
        estado_ph = "Normal" if 6 <= prom_ph <= 9 else "FUERA DE RANGO"
        st.metric("Promedio pH", f"{prom_ph:.2f}", delta=estado_ph, delta_color="normal" if 6 <= prom_ph <= 9 else "inverse")
    
    with col2:
        estado_t = "Óptima" if prom_temp <= 40 else "ALTA"
        st.metric("Temp Promedio", f"{prom_temp:.1f} °C", delta=estado_t, delta_color="normal" if prom_temp <= 40 else "inverse")
        
    with col3:
        st.metric("SST Promedio", f"{df_filtrado['sst'].mean():.2f}")
    with col4:
        st.metric("Total Registros", len(df_filtrado))

    # --- CONTADOR POR PROCESO ---
    st.write("---")
    st.markdown("### 📊 Registros por Proceso")
    conteo = df_filtrado['proceso'].value_counts()
    cols_c = st.columns(len(conteo))
    for i, (proc, cant) in enumerate(conteo.items()):
        cols_c[i].info(f"**{proc}**\n\n{cant}")

    # --- GRÁFICAS Y TABLA ---
    st.write("---")
    c_izq, c_der = st.columns(2)
    
    with c_izq:
        st.subheader("📈 Tendencia pH")
        st.line_chart(df_filtrado.groupby('fecha')['ph'].mean())
        
        st.subheader("🧪 Sólidos por Proceso")
        st.bar_chart(df_filtrado.groupby('proceso')['sst'].mean())

    with c_der:
        st.subheader("🌡️ Temp vs pH")
        st.scatter_chart(data=df_filtrado, x='temp', y='ph', color='proceso')
        
        # BOTÓN DE DESCARGA (NUEVO)
        st.subheader("📋 Datos Filtrados")
        csv = df_filtrado.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar Reporte en CSV", data=csv, file_name="reporte_ptar.csv", mime="text/csv")
        st.dataframe(df_filtrado[['fecha', 'proceso', 'ph', 'temp', 'sst', 'quimicos']], use_container_width=True)

except Exception as e:
    st.error(f"Error: {e}")
