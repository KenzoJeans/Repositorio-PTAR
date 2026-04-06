import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 1. Configuración de página y Estilos
st.set_page_config(page_title="Sistema Control PTAR", layout="wide", page_icon="💧")
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)
st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# 2. Función de limpieza de datos (Pestaña Vertimientos)
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
    
    return df.dropna(subset=['ph']) if 'ph' in df.columns else df

# 3. Conexión y Lógica Principal
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # --- CARGA DE DATOS (VERTIMIENTOS) ---
    # Usamos el nombre de pestaña 'vertimiento' visto en tus capturas
    df_raw = conn.read(worksheet="vertimiento", ttl=0)
    df_base = limpiar_datos_ptar(df_raw)

    # --- BARRA LATERAL ---
    try:
        st.sidebar.image("logo-white-kenzo.png", use_container_width=True)
    except:
        pass

    st.sidebar.header("Filtros de Análisis")
    if not df_base.empty:
        lista_p = sorted(df_base['proceso'].unique().tolist())
        procesos_sel = st.sidebar.multiselect("Filtrar Procesos:", lista_p, default=lista_p)
        df_filtrado = df_base[df_base['proceso'].isin(procesos_sel)]
    else:
        df_filtrado = pd.DataFrame()

    # --- TABS ---
    t1, t2, t3 = st.tabs(["📊 Dashboard Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with t1:
        if not df_filtrado.empty:
            m1, m2, m3 = st.columns(3)
            m1.metric("Promedio pH", f"{df_filtrado['ph'].mean():.2f}")
            if 'temp' in df_filtrado.columns:
                m2.metric("Temp Promedio", f"{df_filtrado['temp'].mean():.1f} °C")
            m3.metric("Total Registros", len(df_filtrado))

            st.subheader("📈 Análisis de pH")
            fig_ph = px.line(df_filtrado.sort_values('fecha'), x='fecha', y='ph', markers=True)
            fig_ph.add_hline(y=9.0, line_dash="dash", line_color="red")
            fig_ph.add_hline(y=6.0, line_dash="dash", line_color="red")
            st.plotly_chart(fig_ph, use_container_width=True)
        else:
            st.info("Cargue datos en la pestaña 'vertimiento' para ver el análisis.")

    with t2:
        st.info("Módulo de Agua Tratada en desarrollo.")

    with t3:
        st.subheader("🛠️ Estado de Maquinaria")
        try:
            # LEER PESTAÑA 'mantenimiento' (Nombre corregido según captura)
            df_m = conn.read(worksheet="mantenimiento", ttl=0)
            df_m.columns = df_m.columns.str.strip().str.upper()
            
            if not df_m.empty:
                # Obtener el reporte más reciente por equipo
                col_ts = 'MARCA TEMPORAL' if 'MARCA TEMPORAL' in df_m.columns else df_m.columns[0]
                df_m[col_ts] = pd.to_datetime(df_m[col_ts], errors='coerce')
                df_m = df_m.sort_values(by=col_ts, ascending=False)
                df_actual = df_m.drop_duplicates(subset=['EQUIPO'])
                
                # Tarjetas de Salud
                cols = st.columns(len(df_actual))
                for i, (_, row) in enumerate(df_actual.iterrows()):
                    with cols[i]:
                        salud_raw = str(row.get('SALUD', '0')).replace('%', '')
                        salud = pd.to_numeric(salud_raw, errors='coerce') or 0
                        color = "green" if salud > 70 else "orange" if salud > 40 else "red"
                        
                        # Bloque HTML corregido para tarjetas
                        st.markdown(f"""
                        <div style="border: 1px solid #444; padding: 15px; border-radius: 10px; background-color: #1e1e1e; text-align: center; min-height: 140px;">
                            <p style="margin: 0; font-weight: bold; color: white; font-size: 14px;">{row['EQUIPO']}</p>
                            <h2 style="color: {color}; margin: 10px 0;">{int(salud)}%</h2>
                            <p style="font-size: 10px; color: #aaa;">Prox: {row.get('FECHA PROX MANTENIMIENTO', 'N/A')}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        st.progress(min(max(salud/100, 0.0), 1.0))

                st.divider()
                st.subheader("📋 Historial de Intervenciones")
                st.dataframe(df_m, use_container_width=True)
            else:
                st.warning("No hay registros en la pestaña 'mantenimiento'.")
        except Exception as e:
            st.error(f"Error en Mantenimiento: {e}")

except Exception as e:
    st.error(f"Error General: {e}")
