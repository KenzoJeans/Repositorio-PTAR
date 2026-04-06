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

# 3. Conexión y Carga de Datos
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_raw = conn.read(ttl=0)
    df_base = limpiar_datos_ptar(df_raw)

    # --- BARRA LATERAL (LOGO Y FILTROS) ---
    try:
        st.sidebar.image("logo-white-kenzo.png", use_container_width=True)
    except:
        st.sidebar.error("Error: No se encontró el archivo del logo.")

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
            m1.metric("Promedio pH", f"{avg_ph:.2f}", delta="EN NORMA" if status_ph == "normal" else "FUERA DE RANGO", delta_color=status_ph)

            status_temp = "normal" if avg_temp <= 40 else "inverse"
            m2.metric("Temp Promedio", f"{avg_temp:.1f} °C", delta="ESTABLE" if status_temp == "normal" else "ELEVADA", delta_color=status_temp)

            status_sst = "normal" if avg_sst <= 50 else "inverse"
            m3.metric("SST Promedio", f"{avg_sst:.2f}", delta="ÓPTIMO" if status_sst == "normal" else "CRÍTICO", delta_color=status_sst)

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
        st.subheader("🛠️ Estado Crítico de Maquinaria")
        
        # Datos simulados de mantenimiento
        equipos = [
            {"nombre": "Bomba de Recirculación B1", "salud": 85, "estado": "Operativo", "fecha": "2026-05-10"},
            {"nombre": "Agitador Tanque Coagulación", "salud": 20, "estado": "Crítico", "fecha": "2026-04-10"},
            {"nombre": "Soplador de Oxidación", "salud": 55, "estado": "Mantenimiento Próximo", "fecha": "2026-04-25"},
            {"nombre": "Filtro de Arena F1", "salud": 95, "estado": "Óptimo", "fecha": "2026-06-15"}
        ]

        # Crear columnas para las tarjetas
        cols = st.columns(len(equipos))
        
        for i, equipo in enumerate(equipos):
            with cols[i]:
                # Color según salud
                color = "green" if equipo['salud'] > 70 else "orange" if equipo['salud'] > 40 else "red"
                
                st.markdown(f"""
                <div style="border: 1px solid #444; padding: 15px; border-radius: 10px; background-color: #1e1e1e; text-align: center;">
                    <p style="margin: 0; font-weight: bold; color: white;">{equipo['nombre']}</p>
                    <h2 style="color: {color}; margin: 10px 0;">{equipo['salud']}%</h2>
                    <p style="font-size: 12px; color: #aaa;">Próximo: {equipo['fecha']}</p>
                </div>
                """, unsafe_allow_html=True)
                st.progress(equipo['salud'] / 100)

        st.divider()
        
        col_list, col_form = st.columns([2, 1])
        
        with col_list:
            st.subheader("📋 Registro de Actividades")
            historial = pd.DataFrame({
                "Fecha": ["2026-04-01", "2026-03-25", "2026-03-15"],
                "Equipo": ["Bomba B1", "Filtro F1", "Agitador"],
                "Acción": ["Cambio de aceite", "Lavado de medios", "Ajuste de bandas"],
                "Responsable": ["Juan P.", "Carlos R.", "Luis M."]
            })
            st.table(historial)

        with col_form:
            st.subheader("📝 Reportar Novedad")
            with st.form("novedad_form"):
                eq_sel = st.selectbox("Equipo", ["Bomba B1", "Agitador", "Filtro F1", "Soplador"])
                obs = st.text_area("Descripción del problema")
                submit = st.form_submit_button("Enviar Reporte")
                if submit:
                    st.success("Reporte enviado al jefe de planta.")

except Exception as e:
    st.error(f"Se detectó un error: {e}")
