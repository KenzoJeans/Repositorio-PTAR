import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_plotly_events import plotly_events

# 1. Configuración de página
st.set_page_config(page_title="Sistema Control PTAR", layout="wide", page_icon="💧")
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)
st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# 2. Función de limpieza de datos
def limpiar_datos_ptar(df):
    if df is None or df.empty: return pd.DataFrame()
    df.columns = df.columns.str.strip()
    mapeo = {
        'ph': 'ph', 'pH': 'ph', 'PH': 'ph', 'temp': 'temp', 'sst': 'sst',
        'Fecha del reporte': 'fecha', 'fecha': 'fecha', 'Proceso a reportar': 'proceso',
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

    # --- BARRA LATERAL (TUS FILTROS) ---
    try:
        st.sidebar.image("logo-white-kenzo.png", use_container_width=True)
    except:
        st.sidebar.error("Logo no encontrado.")

    st.sidebar.header("Filtros de Análisis")
    
    # Filtro de búsqueda por texto (Químicos)
    busqueda_q = st.sidebar.text_input("🔍 Buscar Químico (escribe el nombre):", "")

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

    if busqueda_q and not df_filtrado.empty:
        df_filtrado = df_filtrado[df_filtrado['quimicos'].astype(str).str.contains(busqueda_q, case=False, na=False)]

    # --- CUERPO PRINCIPAL ---
    t1, t2, t3 = st.tabs(["📊 Dashboard Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with t1:
        if not df_filtrado.empty:
            m1, m2, m3, m4 = st.columns(4)
            avg_ph = df_filtrado['ph'].mean()
            m1.metric("Promedio pH", f"{avg_ph:.2f}")
            m2.metric("Temp Promedio", f"{df_filtrado['temp'].mean():.1f} °C")
            m3.metric("SST Promedio", f"{df_filtrado['sst'].mean():.2f}")
            m4.metric("Total Registros", len(df_filtrado))
            st.plotly_chart(px.line(df_filtrado.sort_values('fecha'), x='fecha', y='ph', title="Evolución de pH"), use_container_width=True)
            st.dataframe(df_filtrado, use_container_width=True)
        else:
            st.warning("No hay datos para mostrar.")

    with t2:
        st.info("Módulo de Agua Tratada en desarrollo.")

    with t3:
        st.subheader("🛠️ Plano Interactivo de Mantenimiento")
        st.markdown("Si no ves las burbujas, haz clic en el icono de la casita (Home) en el menú del gráfico.")

        # Coordenadas ajustadas para el diagrama lateral
        equipos_data = {
            'Equipo': ['Homogeneización', 'Coagulación', 'Sedimentador', 'Oxidación', 'Filtración', 'Agua Tratada', 'Bomba B1', 'Bomba B2'],
            'X': [8, 25, 45, 62, 78, 92, 53, 64],
            'Y': [40, 60, 50, 55, 50, 45, 25, 25],
            'Estado': ['Al día', 'Próximo', 'Al día', 'Al día', 'Vencido', 'Al día', 'Al día', 'Próximo']
        }
        df_eq = pd.DataFrame(equipos_data)
        colores_map = {'Al día': '#00FF00', 'Próximo': '#FFFF00', 'Vencido': '#FF0000'}

        # Gráfico con alta visibilidad
        fig_p = px.scatter(
            df_eq, x='X', y='Y', text='Equipo', color='Estado',
            color_discrete_map=colores_map,
            range_x=[0, 100], range_y=[0, 100]
        )

        fig_p.update_traces(
            marker=dict(size=45, line=dict(width=3, color='white'), opacity=0.9),
            textposition='top center',
            textfont=dict(size=14, color='white')
        )

        fig_p.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(30,30,30,1)', # Fondo gris oscuro para que resalte
            xaxis=dict(showgrid=False, zeroline=False, visible=False),
            yaxis=dict(showgrid=False, zeroline=False, visible=False),
            showlegend=True,
            height=600
        )

        # CAPTURA DE EVENTO
        clic = plotly_events(fig_p, click_event=True, override_height=600)

        if clic:
            idx = clic[0]['pointIndex']
            equipo_sel = df_eq.iloc[idx]['Equipo']
            st.success(f"### 📑 Historial: {equipo_sel}")
            st.table(pd.DataFrame([{"Fecha": "2026-04-06", "Tarea": "Verificación de sensores", "Estatus": "Completado"}]))
        else:
            st.info("Haz clic en una de las burbujas de colores para ver el historial.")

except Exception as e:
    st.error(f"Error crítico: {e}")
