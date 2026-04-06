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
    
    # Carga de datos principales (Vertimientos)
    df_raw = conn.read(worksheet="vertimiento", ttl=0) 
    df_base = limpiar_datos_ptar(df_raw)

    # --- BARRA LATERAL (LOGO Y FILTROS) ---
    try:
        st.sidebar.image("logo-white-kenzo.png", use_container_width=True)
    except:
        st.sidebar.error("Error: No se encontró el archivo del logo en el repositorio.")

    st.sidebar.header("Filtros de Análisis")
    
    # Filtro de Fecha
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

    # --- FILTRO POR QUÍMICOS ---
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
            m1.metric("Promedio pH", f"{avg_ph:.2f}", 
                      delta="EN NORMA" if status_ph == "normal" else "FUERA DE RANGO",
                      delta_color=status_ph)

            status_temp = "normal" if avg_temp <= 40 else "inverse"
            m2.metric("Temp Promedio", f"{avg_temp:.1f} °C",
                      delta="ESTABLE" if status_temp == "normal" else "ELEVADA",
                      delta_color=status_temp)

            status_sst = "normal" if avg_sst <= 50 else "inverse"
            m3.metric("SST Promedio", f"{avg_sst:.2f}",
                      delta="ÓPTIMO" if status_sst == "normal" else "CRÍTICO",
                      delta_color=status_sst)

            m4.metric("Total Registros", len(df_filtrado))

            st.subheader("📈 Análisis de pH")
            fig_t = px.line(df_filtrado.sort_values('fecha'), x='fecha', y='ph', markers=True, title="Evolución Histórica de pH")
            fig_t.add_hline(y=9.0, line_dash="dash", line_color="red")
            fig_t.add_hline(y=6.0, line_dash="dash", line_color="red")
            st.plotly_chart(fig_t, use_container_width=True)

            df_p = df_filtrado.groupby('proceso')['ph'].mean().reset_index()
            fig_p = px.scatter(df_p, x='proceso', y='ph', color='ph', 
                               color_continuous_scale='RdYlGn_r', range_color=[5, 10], size=[15]*len(df_p),
                               title="Promedio de pH por Etapa")
            fig_p.update_traces(mode='lines+markers', line_color='lightgrey')
            st.plotly_chart(fig_p, use_container_width=True)

            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("📊 Sólidos (SST)")
                df_s = df_filtrado.groupby('proceso')['sst'].mean().reset_index()
                fig_s = px.bar(df_s, x='proceso', y='sst', color='sst', title="Promedio SST por Etapa")
                st.plotly_chart(fig_s, use_container_width=True)

            with col_b:
                st.subheader("🌡️ Temperatura")
                df_temp_plot = df_filtrado.groupby('proceso')['temp'].mean().reset_index()
                fig_temp = px.line(df_temp_plot, x='proceso', y='temp', markers=True, title="Temperatura por Etapa")
                st.plotly_chart(fig_temp, use_container_width=True)

            st.subheader("📋 Detalle de Datos")
            st.dataframe(df_filtrado, use_container_width=True)
        else:
            st.warning("No hay datos para los filtros seleccionados.")

    with t2:
        st.info("Módulo de Agua Tratada en desarrollo.")

    with t3:
        st.subheader("🛠️ Bitácora de Mantenimiento de Equipos")
        try:
            # Carga específica de la pestaña de mantenimiento
            df_mantenimiento = conn.read(worksheet="mantenimiento", ttl=0)
            df_mantenimiento.columns = df_mantenimiento.columns.str.strip().str.upper()

            if not df_mantenimiento.empty:
                # 1. KPIs de Salud de Maquinaria (Último reporte por equipo)
                # Asumiendo que la columna 'MARCA TEMPORAL' o 'FECHA' indica la última entrada
                col_fecha_m = 'MARCA TEMPORAL' if 'MARCA TEMPORAL' in df_mantenimiento.columns else df_mantenimiento.columns[0]
                df_mantenimiento[col_fecha_m] = pd.to_datetime(df_mantenimiento[col_fecha_m])
                
                # Obtener el estado más reciente de cada equipo
                df_estado_actual = df_mantenimiento.sort_values(col_fecha_m).drop_duplicates('EQUIPO', keep='last')

                # Renderizado de Tarjetas Visuales
                st.write("### ❤️ Estado de Salud de Equipos")
                columnas_equipo = st.columns(len(df_estado_actual))
                
                for idx, (_, row) in enumerate(df_estado_actual.iterrows()):
                    with columnas_equipo[idx]:
                        # Limpiar valor de salud (eliminar % si existe)
                        salud_val = str(row['SALUD']).replace('%', '')
                        salud_num = pd.to_numeric(salud_val, errors='coerce') or 0
                        
                        color_salud = "green" if salud_num >= 80 else "orange" if salud_num >= 50 else "red"
                        
                        st.markdown(f"""
                            <div style="border: 1px solid #ddd; padding: 10px; border-radius: 10px; text-align: center; background-color: #f9f9f9;">
                                <p style="margin: 0; font-weight: bold; color: #333;">{row['EQUIPO']}</p>
                                <h2 style="margin: 0; color: {color_salud};">{int(salud_num)}%</h2>
                                <p style="margin: 0; font-size: 12px; color: #666;">Estado: {row['ESTADO']}</p>
                            </div>
                        """, unsafe_allow_html=True)
                        st.progress(min(max(salud_num/100, 0.0), 1.0))

                st.divider()

                # 2. Histórico y Filtro de Búsqueda
                st.write("### 📋 Historial Completo de Intervenciones")
                busqueda_m = st.text_input("🔍 Buscar por equipo u operario:")
                
                if busqueda_m:
                    df_m_mostrar = df_mantenimiento[df_mantenimiento.astype(str).apply(lambda x: x.str.contains(busqueda_m, case=False)).any(axis=1)]
                else:
                    df_m_mostrar = df_mantenimiento

                st.dataframe(df_m_mostrar.sort_values(col_fecha_m, ascending=False), use_container_width=True)
            else:
                st.warning("No hay registros en la pestaña de 'mantenimiento'.")
        
        except Exception as e_m:
            st.error(f"Error al cargar el módulo de mantenimiento: {e_m}")

except Exception as e:
    st.error(f"Se detectó un error en la aplicación: {e}")
