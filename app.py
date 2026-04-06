import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_plotly_events import plotly_events

# 1. Configuración de página
st.set_page_config(page_title="Sistema Control PTAR", layout="wide", page_icon="💧")
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)
st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# 2. Función de limpieza de datos mejorada
def limpiar_datos_ptar(df):
    if df is None or df.empty: return pd.DataFrame()
    
    # Limpiar nombres de columnas (quitar espacios y pasar a minúsculas para comparar)
    df.columns = df.columns.str.strip()
    
    # Mapeo flexible
    mapeo = {
        'ph': 'ph', 'pH': 'ph', 'PH': 'ph',
        'temp': 'temp', 'temperatura': 'temp', 'Temperatura': 'temp',
        'sst': 'sst', 'Solidos suspendidos': 'sst', 'SST': 'sst',
        'Fecha del reporte': 'fecha', 'fecha': 'fecha',
        'Proceso a reportar': 'proceso',
        'Productos quimicos utilizados en el proceso': 'quimicos'
    }
    
    df = df.rename(columns={k: v for k, v in mapeo.items() if k in df.columns})

    # Convertir a números solo las que existan
    for col in ['ph', 'temp', 'sst']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce').dt.date
    
    return df

# 3. Conexión y Carga de Datos
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_raw = conn.read(ttl=0)
    df_base = limpiar_datos_ptar(df_raw)

    # --- BARRA LATERAL (TUS FILTROS) ---
    try:
        st.sidebar.image("logo-white-kenzo.png", use_container_width=True)
    except:
        pass

    st.sidebar.header("Filtros de Análisis")
    busqueda_q = st.sidebar.text_input("🔍 Buscar Químico:", "")

    if not df_base.empty and 'fecha' in df_base.columns:
        df_base = df_base.dropna(subset=['fecha'])
        if not df_base.empty:
            min_f, max_f = min(df_base['fecha']), max(df_base['fecha'])
            rango_fechas = st.sidebar.date_input("Rango de fechas:", [min_f, max_f])
            if len(rango_fechas) == 2:
                df_base = df_base[(df_base['fecha'] >= rango_fechas[0]) & (df_base['fecha'] <= rango_fechas[1])]

    if not df_base.empty and 'proceso' in df_base.columns:
        lista_p = sorted(df_base['proceso'].dropna().unique().tolist())
        procesos_sel = st.sidebar.multiselect("Procesos:", lista_p, default=lista_p)
        df_filtrado = df_base[df_base['proceso'].isin(procesos_sel)]
    else:
        df_filtrado = df_base

    if busqueda_q and not df_filtrado.empty and 'quimicos' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['quimicos'].astype(str).str.contains(busqueda_q, case=False, na=False)]

    # --- CUERPO PRINCIPAL ---
    t1, t2, t3 = st.tabs(["📊 Dashboard Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with t1:
        if not df_filtrado.empty:
            m1, m2, m3, m4 = st.columns(4)
            
            # Cálculo seguro de métricas
            ph_val = f"{df_filtrado['ph'].mean():.2f}" if 'ph' in df_filtrado.columns else "N/A"
            temp_val = f"{df_filtrado['temp'].mean():.1f} °C" if 'temp' in df_filtrado.columns else "N/A"
            sst_val = f"{df_filtrado['sst'].mean():.2f}" if 'sst' in df_filtrado.columns else "N/A"
            
            m1.metric("Promedio pH", ph_val)
            m2.metric("Temp Promedio", temp_val)
            m3.metric("SST Promedio", sst_val)
            m4.metric("Total Registros", len(df_filtrado))
            
            if 'ph' in df_filtrado.columns and 'fecha' in df_filtrado.columns:
                st.plotly_chart(px.line(df_filtrado.sort_values('fecha'), x='fecha', y='ph', title="Evolución de pH"), use_container_width=True)
            
            st.dataframe(df_filtrado, use_container_width=True)
        else:
            st.warning("No hay datos suficientes para mostrar el Dashboard.")

    with t2:
        st.info("Módulo de Agua Tratada en desarrollo.")

    with t3:
        st.subheader("🛠️ Plano Interactivo de Mantenimiento")
        equipos_data = {
            'Equipo': ['Homogeneización', 'Coagulación', 'Sedimentador', 'Oxidación', 'Filtración', 'Agua Tratada', 'Bomba B1', 'Bomba B2'],
            'X': [8, 25, 45, 62, 78, 92, 53, 64],
            'Y': [40, 60, 50, 55, 50, 45, 25, 25],
            'Estado': ['Al día', 'Próximo', 'Al día', 'Al día', 'Vencido', 'Al día', 'Al día', 'Próximo']
        }
        df_eq = pd.DataFrame(equipos_data)
        fig_p = px.scatter(df_eq, x='X', y='Y', text='Equipo', color='Estado', 
                           color_discrete_map={'Al día': '#00FF00', 'Próximo': '#FFFF00', 'Vencido': '#FF0000'},
                           range_x=[0, 100], range_y=[0, 100])
        fig_p.update_traces(marker=dict(size=40, line=dict(width=2, color='white')), textposition='top center')
        fig_p.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(35,35,35,1)', xaxis=dict(visible=False), yaxis=dict(visible=False), height=550)

        clic = plotly_events(fig_p, click_event=True, override_height=550)
        if clic:
            idx = clic[0]['pointIndex']
            st.success(f"### 📑 Historial: {df_eq.iloc[idx]['Equipo']}")
            st.table(pd.DataFrame([{"Fecha": "2026-04-06", "Tarea": "Mantenimiento Preventivo"}]))

except Exception as e:
    st.error(f"Hubo un problema con los datos: {e}. Revisa que las columnas en tu Sheets no hayan cambiado de nombre.")
