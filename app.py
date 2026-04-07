import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 1. Configuración de página y Estilo
st.set_page_config(page_title="Sistema Control PTAR", layout="wide", page_icon="💧")
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)
st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# --- CONFIGURACIÓN DE CONEXIÓN ---
# IMPORTANTE: Reemplaza con tus URLs reales
URL_DIRECTA_MANTO = "TU_URL_AQUI_CON_EL_GID" 
URL_DIRECTA_TRATADA = "TU_URL_AGUA_TRATADA_AQUI"

# 2. Función de limpieza de datos REFORZADA (LÓGICA BASE + ANTIBALAS)
def limpiar_datos_ptar(df):
    if df is None or df.empty:
        return pd.DataFrame()
    
    df.columns = df.columns.str.strip()
    # Mapeo flexible extendido para evitar errores de nombres o 'sst'
    mapeo = {
        'ph': 'ph', 'pH': 'ph', 'PH': 'ph',
        'temp': 'temp', 'Temperatura': 'temp', 'TEMP': 'temp',
        'sst': 'sst', 'SST': 'sst', 'Solidos': 'sst', 'Solidos suspendidos': 'sst',
        'Fecha del reporte': 'fecha', 'fecha': 'fecha', 'Marca temporal': 'fecha',
        'Proceso a reportar': 'proceso',
        'Productos quimicos utilizados en el proceso': 'quimicos'
    }
    df = df.rename(columns={k: v for k, v in mapeo.items() if k in df.columns})

    # Asegurar que las columnas críticas existan y sean numéricas (maneja ceros y vacíos)
    for col in ['ph', 'temp', 'sst']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        else:
            # Si no existe la columna, la crea con 0 para que la app no se rompa
            df[col] = 0.0
    
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce').dt.date
    
    return df

# 3. Conexión y Carga de Datos
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Carga Vertimiento (Hoja principal de Secrets)
    df_raw = conn.read(ttl=0) 
    df_base = limpiar_datos_ptar(df_raw)

    # Carga Agua Tratada (URL Directa)
    try:
        df_trat_raw = conn.read(spreadsheet=URL_DIRECTA_TRATADA, ttl=0)
        df_tratada = limpiar_datos_ptar(df_trat_raw)
    except:
        df_tratada = pd.DataFrame()

    # Carga Mantenimiento (URL Directa anti-Error 400)
    try:
        df_manto = conn.read(spreadsheet=URL_DIRECTA_MANTO, ttl=0)
        df_manto.columns = df_manto.columns.str.strip()
    except:
        df_manto = pd.DataFrame()

    # --- BARRA LATERAL (FILTROS BASE) ---
    try:
        st.sidebar.image("logo-white-kenzo.png", use_container_width=True)
    except:
        pass

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

    # --- CUERPO PRINCIPAL (TABS) ---
    t1, t2, t3 = st.tabs(["📊 Dashboard Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with t1:
        if not df_filtrado.empty:
            # MÉTRICAS CON INDICADORES (DELTAS)
            m1, m2, m3, m4 = st.columns(4)
            avg_ph = df_filtrado['ph'].mean()
            avg_temp = df_filtrado['temp'].mean()
            avg_sst = df_filtrado['sst'].mean()

            m1.metric("Promedio pH", f"{avg_ph:.2f}", 
                      delta="EN NORMA" if 6.0 <= avg_ph <= 9.0 else "FUERA DE RANGO",
                      delta_color="normal" if 6.0 <= avg_ph <= 9.0 else "inverse")
            m2.metric("Temp Promedio", f"{avg_temp:.1f} °C",
                      delta="ESTABLE" if avg_temp <= 40 else "ELEVADA")
            m3.metric("SST Promedio", f"{avg_sst:.2f}",
                      delta="ÓPTIMO" if avg_sst <= 50 else "CRÍTICO")
            m4.metric("Total Registros", len(df_filtrado))

            # GRÁFICAS BASE
            st.subheader("📈 Análisis de pH")
            fig_t = px.line(df_filtrado.sort_values('fecha'), x='fecha', y='ph', markers=True, template="plotly_dark")
            fig_t.add_hline(y=9.0, line_dash="dash", line_color="red")
            fig_t.add_hline(y=6.0, line_dash="dash", line_color="red")
            st.plotly_chart(fig_t, use_container_width=True)

            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("📊 Sólidos (SST)")
                df_s = df_filtrado.groupby('proceso')['sst'].mean().reset_index()
                fig_s = px.bar(df_s, x='proceso', y='sst', color='sst', template="plotly_dark")
                st.plotly_chart(fig_s, use_container_width=True)
            with col_b:
                st.subheader("🌡️ Temperatura")
                df_temp_plot = df_filtrado.groupby('proceso')['temp'].mean().reset_index()
                fig_temp = px.line(df_temp_plot, x='proceso', y='temp', markers=True, template="plotly_dark")
                st.plotly_chart(fig_temp, use_container_width=True)
            
            st.dataframe(df_filtrado, use_container_width=True)
        else:
            st.warning("No hay datos para mostrar en Vertimientos.")

    with t2:
        st.subheader("🧪 Eficiencia de Tratamiento (Salida)")
        if not df_tratada.empty:
            # LÓGICA DE EFICIENCIA (Comparación Entrada vs Salida)
            sst_entrada = df_filtrado['sst'].mean() if not df_filtrado.empty else 0
            sst_salida = df_tratada['sst'].mean()
            
            # Cálculo de remoción protegiendo contra división por cero
            remocion = ((sst_entrada - sst_salida) / sst_entrada) * 100 if sst_entrada > 0 else 0

            c1, c2, c3 = st.columns(3)
            c1.metric("SST Salida", f"{sst_salida:.1f} mg/L", delta=f"{remocion:.1f}% Remoción")
            c2.metric("pH Salida", f"{df_tratada['ph'].mean():.2f}")
            c3.metric("Estado Salida", "DENTRO DE NORMA" if sst_salida <= 50 else "FUERA DE LÍMITE")

            st.markdown("---")
            st.write("**Historial de Agua Tratada:**")
            st.dataframe(df_tratada, use_container_width=True)
        else:
            st.info("No hay datos en la pestaña de Agua Tratada o la URL es incorrecta.")

    with t3:
        st.subheader("🛠️ Panel de Mantenimiento por Equipo")
        
        if not df_manto.empty:
            # Asegurar datos numéricos para Salud
            if 'SALUD' in df_manto.columns:
                df_manto['SALUD'] = pd.to_numeric(df_manto['SALUD'], errors='coerce').fillna(0)

            # 1. RESUMEN GLOBAL (CARDS)
            avg_s_global = df_manto['SALUD'].mean() if 'SALUD' in df_manto.columns else 0
            
            st.markdown(f"""
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 20px;">
                    <div style="background-color: #1E1E1E; padding: 15px; border-radius: 10px; border-left: 5px solid #4CAF50;">
                        <small style="color: #888;">Salud Global</small><br>
                        <strong style="font-size: 20px;">{avg_s_global:.1f}/10</strong>
                    </div>
                    <div style="background-color: #1E1E1E; padding: 15px; border-radius: 10px; border-left: 5px solid #2196F3;">
                        <small style="color: #888;">Equipos Activos</small><br>
                        <strong style="font-size: 20px;">{len(df_manto['EQUIPO'].unique()) if 'EQUIPO' in df_manto.columns else 0}</strong>
                    </div>
                    <div style="background-color: #1E1E1E; padding: 15px; border-radius: 10px; border-left: 5px solid #9C27B0;">
                        <small style="color: #888;">Reportes Totales</small><br>
                        <strong style="font-size: 20px;">{len(df_manto)}</strong>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # 2. TARJETAS INDIVIDUALES POR EQUIPO
            if 'EQUIPO' in df_manto.columns:
                st.markdown("### Estado de Equipos Registrados")
                equipos = df_manto['EQUIPO'].unique()
                cols_eq = st.columns(3)

                for i, eq_nombre in enumerate(equipos):
                    datos = df_manto[df_manto['EQUIPO'] == eq_nombre].iloc[-1]
                    salud_val = datos['SALUD']
                    color_card = "#4CAF50" if salud_val >= 8 else "#FFEB3B" if salud_val >= 6 else "#F44336"
                    
                    f_reporte = datos.get('Fecha', datos.get('Marca temporal', 'N/A'))
                    tarea = datos.get('QUE SE REALIZO', 'Sin descripción')
                    proximo = datos.get('FECHA PROX MANTENIMIENTO', 'N/A')

                    with cols_eq[i % 3]:
                        st.markdown(f"""
                            <div style="background-color: #1E1E1E; padding: 15px; border-radius: 10px; border-top: 5px solid {color_card}; margin-bottom: 15px;">
                                <h4 style="margin-bottom: 5px;">⚙️ {eq_nombre}</h4>
                                <p style="font-size: 14px; margin: 0; color: {color_card};">Salud Actual: <b>{salud_val}/10</b></p>
                                <p style="font-size: 11px; color: #888; margin-top: 5px;">Último registro: {f_reporte}</p>
                                <hr style="margin: 10px 0; border: 0.5px solid #333;">
                                <p style="font-size: 11px; height: 40px; overflow: hidden;">{tarea[:85]}...</p>
                                <p style="font-size: 10px; color: #555; text-align: right; margin-top: 5px;">Próximo Manto: {proximo}</p>
                            </div>
                        """, unsafe_allow_html=True)
            
            with st.expander("Ver Historial Completo de Mantenimiento"):
                st.dataframe(df_manto, use_container_width=True)
        else:
            st.warning("No se encontraron registros en la pestaña de mantenimiento.")

except Exception as e:
    st.error(f"Error general en la aplicación: {e}")
