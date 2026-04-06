import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_plotly_events import plotly_events
from PIL import Image

# 1. Configuración de página y estilos corporativos
st.set_page_config(page_title="Sistema Control PTAR", layout="wide", page_icon="💧")
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)
st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# 2. Funciones de limpieza y lógica de datos
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

# Lógica del Plano Interactivo de Mantenimiento (Coordenadas)
def obtener_equipo_clic(x, y):
    """Retorna el nombre del equipo basado en las coordenadas de la imagen (simplificado)"""
    # X va de 0 a 100, Y va de 0 a 100
    if 0 <= x <= 15 and 60 <= y <= 90: return "Tanque Homogeneización"
    if 20 <= x <= 30 and 15 <= y <= 45: return "Tanque Coagulación (Agitador)"
    if 30 <= x <= 50 and 30 <= y <= 70: return "Sedimentador"
    if 50 <= x <= 65 and 30 <= y <= 70: return "Tanque Oxidación"
    if 65 <= x <= 80 and 30 <= y <= 70: return "Sistema Filtración (Batería)"
    if 80 <= x <= 90 and 40 <= y <= 70: return "Tanque Agua Tratada"
    if 51 <= x <= 57 and 67 <= y <= 75: return "Bomba B1"
    if 61 <= x <= 67 and 67 <= y <= 75: return "Bomba B2"
    return None

# 3. Conexión y Carga de Datos
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_raw = conn.read(ttl=0)
    df_base = limpiar_datos_ptar(df_raw)

    # --- BARRA LATERAL (LOGO Y FILTROS) ---
    try:
        st.sidebar.image("logo_kenzo.png", use_container_width=True)
    except:
        st.sidebar.error("Error: Logo no encontrado. Verifica el nombre en GitHub.")

    st.sidebar.header("Filtros de Análisis")
    
    # Filtro de Fecha
    if not df_base.empty and 'fecha' in df_base.columns:
        min_f, max_f = min(df_base['fecha']), max(df_base['fecha'])
        rango_fechas = st.sidebar.date_input("Rango de fechas:", [min_f, max_f])
        if len(rango_fechas) == 2:
            df_base = df_base[(df_base['fecha'] >= rango_fechas[0]) & (df_base['fecha'] <= rango_fechas[1])]

    # Filtro de Proceso (Multiselect)
    if not df_base.empty and 'proceso' in df_base.columns:
        lista_p = sorted(df_base['proceso'].unique().tolist())
        procesos_sel = st.sidebar.multiselect("Selecciona el Proceso:", lista_p, default=lista_p)
        df_filtrado = df_base[df_base['proceso'].isin(procesos_sel)]
    else:
        df_filtrado = df_base

    # --- FILTRO POR BÚSQUEDA DE TEXTO (QUÍMICOS) ---
    if not df_filtrado.empty and 'quimicos' in df_filtrado.columns:
        busqueda_q = st.sidebar.text_input("🔍 Buscar Químico (escribe el nombre):", "")
        if busqueda_q:
            df_filtrado = df_filtrado[df_filtrado['quimicos'].astype(str).str.contains(busqueda_q, case=False, na=False)]

    # --- CUERPO PRINCIPAL ---
    t1, t2, t3 = st.tabs(["📊 Dashboard Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento Interactivo"])

    with t1:
        if not df_filtrado.empty:
            # Métricas
            m1, m2, m3, m4 = st.columns(4)
            avg_ph = df_filtrado['ph'].mean()
            status_ph = "normal" if 6.0 <= avg_ph <= 9.0 else "inverse"
            m1.metric("Promedio pH", f"{avg_ph:.2f}", 
                      delta="EN NORMA" if status_ph == "normal" else "FUERA DE RANGO",
                      delta_color=status_ph)
            m2.metric("Temp Promedio", f"{df_filtrado['temp'].mean():.1f} °C")
            m3.metric("SST Promedio", f"{df_filtrado['sst'].mean():.2f}")
            m4.metric("Total Registros", len(df_filtrado))

            # Gráfica de pH
            st.subheader("📈 Análisis de pH")
            fig_t = px.line(df_filtrado.sort_values('fecha'), x='fecha', y='ph', markers=True, title="Evolución de pH")
            fig_t.add_hline(y=9.0, line_dash="dash", line_color="red")
            fig_t.add_hline(y=6.0, line_dash="dash", line_color="red")
            st.plotly_chart(fig_t, use_container_width=True)

            # Tabla de Datos
            st.subheader("📋 Detalle de Datos")
            st.dataframe(df_filtrado, use_container_width=True)
        else:
            st.warning("No hay datos para los filtros seleccionados.")

    with t2:
        st.info("Módulo de Agua Tratada en desarrollo.")

    # --- T3: MANTENIMIENTO INTERACTIVO (PLANO) ---
    with t3:
        st.subheader("🛠️ Bitácora de Mantenimiento Interactiva")
        st.markdown("Haz clic sobre una unidad o equipo en el plano lateral de la PTAR para ver su historial.")

        # Cargar y configurar la imagen del plano lateral
        try:
            plano_imagen = Image.open("diagrama_lateral_ptar.png")
            
            # Crear un gráfico de Plotly con la imagen como fondo para capturar clics
            fig_plano = px.scatter(x=[0, 100], y=[0, 100], labels={"x": "X", "y": "Y"}, range_x=[0, 100], range_y=[0, 100])
            fig_plano.update_layout(images=[dict(source=plano_imagen, xref="x", yref="y", x=0, y=100, sizex=100, sizey=100, sizing="stretch", opacity=1, layer="below")])
            fig_plano.update_traces(marker=dict(size=1, color="rgba(0,0,0,0)")) # Puntos invisibles
            fig_plano.update_xaxes(visible=False); fig_plano.update_yaxes(visible=False) # Ocultar ejes
            
            # Capturar evento de clic sobre el plano
            selected_point = plotly_events(fig_plano, click_event=True, hover_event=False, select_event=False, override_height=400, override_width="100%")

            equipo_seleccionado = None
            if selected_point:
                x_clic, y_clic = selected_point[0]['x'], selected_point[0]['y']
                equipo_seleccionado = obtener_equipo_clic(x_clic, y_clic)
            
            # Mostrar historial basado en el equipo seleccionado
            if equipo_seleccionado:
                st.markdown(f"**### Historial para: {equipo_seleccionado}**")
                # -- AQUÍ DEBERÍA IR LA CARGA DE DATOS REALES DE MANTENIMIENTO --
                # Por ahora, simulamos una bitácora básica
                historial_simulado = {
                    "Tanque Homogeneización": [{"Fecha": "2026-03-01", "Actividad": "Limpieza de lodos sedimentados", "Responsable": "Luis M."}, {"Fecha": "2026-01-15", "Actividad": "Ajuste de sensor de nivel", "Responsable": "Jorge P."}],
                    "Bomba B1": [{"Fecha": "2026-03-10", "Actividad": "Cambio de sellos mecánicos", "Responsable": "Técnico Ext."}, {"Fecha": "2026-02-10", "Actividad": "Revisión de consumo eléctrico", "Responsable": "Luis M."}]
                }
                
                if equipo_seleccionado in historial_simulado:
                    df_h = pd.DataFrame(historial_simulado[equipo_seleccionado])
                    st.dataframe(df_h, use_container_width=True)
                else:
                    st.info("No se registran actividades de mantenimiento para este equipo.")
            else:
                st.info("Haz clic en un equipo del plano (ej: Tanque Coagulación, Sedimentador, Bombas, Filtros) para iniciar.")

        except:
            st.error("Error: No se pudo cargar el archivo 'diagrama_lateral_ptar.png' desde el repositorio.")

except Exception as e:
    st.error(f"Se detectó un error en la aplicación: {e}")
