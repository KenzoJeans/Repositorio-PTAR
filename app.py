import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 1. Configuración de página
st.set_page_config(page_title="Sistema Control PTAR", layout="wide", page_icon="💧")
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)

# 2. Función de limpieza (con protección contra el error 'temp')
def limpiar_datos_ptar(df):
    if df is None or df.empty: return pd.DataFrame()
    df.columns = df.columns.str.strip()
    mapeo = {
        'ph': 'ph', 'pH': 'ph', 'temp': 'temp', 'Temperatura': 'temp',
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
    return df

# 3. Carga de Datos
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_raw = conn.read(ttl=0)
    df_base = limpiar_datos_ptar(df_raw)

    # --- BARRA LATERAL (TUS FILTROS) ---
    st.sidebar.header("Filtros de Análisis")
    busqueda_q = st.sidebar.text_input("🔍 Buscar Químico:", "")

    # --- CUERPO PRINCIPAL ---
    t1, t2, t3 = st.tabs(["📊 Dashboard", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with t1:
        st.write("Dashboard cargado.")
        st.dataframe(df_base.head())

    with t3:
        st.subheader("🛠️ Estado de Equipos (Mapa de Mantenimiento)")
        st.info("Selecciona un equipo de la lista para ver su historial detallado.")

        # Datos de equipos para el "Mapa"
        equipos_ptar = pd.DataFrame({
            'Equipo': ['Homogeneización', 'Coagulación', 'Sedimentador', 'Oxidación', 'Filtración', 'Agua Tratada', 'Bomba B1', 'Bomba B2'],
            'Nivel de Salud': [100, 70, 100, 100, 30, 100, 90, 60], # Para que se vea algo físico
            'Estado': ['Al día', 'Próximo', 'Al día', 'Al día', 'Vencido', 'Al día', 'Al día', 'Próximo']
        })

        # Gráfico de barras horizontal que no falla
        fig_mapa = px.bar(
            equipos_ptar, 
            x='Nivel de Salud', 
            y='Equipo', 
            color='Estado',
            orientation='h',
            color_discrete_map={'Al día': '#00FF00', 'Próximo': '#FFFF00', 'Vencido': '#FF0000'},
            text='Estado'
        )

        fig_mapa.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color="white"),
            xaxis=dict(visible=False),
            height=450
        )

        # Usamos un selectbox de Streamlit para la interacción (es 100% confiable)
        equipo_sel = st.selectbox("👉 Selecciona un equipo para ver bitácora:", equipos_ptar['Equipo'])

        st.plotly_chart(fig_mapa, use_container_width=True, config={'displayModeBar': False})

        if equipo_sel:
            st.markdown(f"### 📑 Historial de Mantenimiento: {equipo_sel}")
            # Simulación de datos
            st.table(pd.DataFrame([{"Fecha": "2026-04-06", "Actividad": "Limpieza y calibración", "Responsable": "Operador Planta"}]))

except Exception as e:
    st.error(f"Error: {e}")
