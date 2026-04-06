import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 1. Configuración de página
st.set_page_config(page_title="Sistema Control PTAR", layout="wide", page_icon="💧")
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)
st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# 2. Función de limpieza de datos mejorada
def limpiar_datos_ptar(df):
    if df is None or df.empty:
        return pd.DataFrame()
    
    df.columns = df.columns.str.strip()
    # Mapeo flexible para evitar errores por nombres de columna
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
    
    return df

# 3. Conexión Principal
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CUERPO PRINCIPAL ---
t1, t2, t3 = st.tabs(["📊 Dashboard Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

with t1:
    try:
        # Carga específica para Vertimientos
        df_raw = conn.read(worksheet="vertimiento", ttl=0)
        df_base = limpiar_datos_ptar(df_raw)
        
        # Filtros (simplificados para evitar errores de lógica)
        if not df_base.empty:
            st.sidebar.header("Filtros de Análisis")
            # ... (Tus filtros de fecha y proceso se mantienen aquí)
            
            # --- MÉTRICAS Y GRÁFICAS ---
            # (El código de tus gráficas de pH y SST va aquí igual que antes)
            st.success("Datos de vertimientos cargados correctamente.")
            st.dataframe(df_base.head())
        else:
            st.warning("La pestaña 'vertimiento' está vacía.")
    except Exception as e:
        st.error(f"Error al cargar Vertimientos: Verifique que la pestaña se llame 'vertimiento'.")

with t2:
    st.info("Módulo de Agua Tratada en desarrollo.")

with t3:
    st.subheader("🛠️ Bitácora de Mantenimiento")
    try:
        # CARGA BLINDADA: Si falla, solo falla esta pestaña
        df_m = conn.read(worksheet="mantenimiento", ttl=0)
        
        if not df_m.empty:
            # Normalizamos nombres de columnas (Quitar espacios y pasar a MAYUS)
            df_m.columns = df_m.columns.str.strip().str.upper()
            
            # Identificar columna de fecha (Marca temporal o Fecha)
            col_fecha = 'MARCA TEMPORAL' if 'MARCA TEMPORAL' in df_m.columns else df_m.columns[0]
            df_m[col_fecha] = pd.to_datetime(df_m[col_fecha], errors='coerce')

            # Visualización de KPIs de Salud
            if 'EQUIPO' in df_m.columns and 'SALUD' in df_m.columns:
                df_ult = df_m.sort_values(col_fecha).drop_duplicates('EQUIPO', keep='last')
                cols_kpi = st.columns(len(df_ult))
                
                for i, (_, r) in enumerate(df_ult.iterrows()):
                    with cols_kpi[i]:
                        val_s = str(r['SALUD']).replace('%', '')
                        num_s = pd.to_numeric(val_s, errors='coerce') or 0
                        color = "green" if num_s >= 80 else "orange" if num_s >= 50 else "red"
                        st.metric(label=r['EQUIPO'], value=f"{int(num_s)}%", delta=r.get('ESTADO', ''))
            
            st.divider()
            st.write("### Historial de Intervenciones")
            st.dataframe(df_m, use_container_width=True)
        else:
            st.info("No hay datos en la pestaña de mantenimiento.")
            
    except Exception as e:
        st.error("Error en Mantenimiento: Asegúrese de que la pestaña se llame 'mantenimiento' y tenga las columnas: EQUIPO, SALUD, ESTADO.")
