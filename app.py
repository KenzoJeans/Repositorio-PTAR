import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Sistema Control PTAR", layout="wide", page_icon="💧")

# Estilo para reducir espacios superiores
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)
st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# 2. FUNCIONES DE PROCESAMIENTO
def limpiar_datos_ptar(df):
    if df is None or df.empty:
        return pd.DataFrame()
    
    # Limpiar nombres de columnas
    df.columns = df.columns.str.strip()
    
    # Mapeo de columnas basado en tus capturas
    mapeo = {
        'PH': 'ph', 'ph': 'ph',
        'TEMPERATURA': 'temp', 'temp': 'temp',
        'SOLIDOS SUSPENDIDOS': 'sst', 'sst': 'sst',
        'FECHA DEL REPORTE': 'fecha',
        'PROCESO A REPORTAR': 'proceso',
        'PRODUCTOS QUIMICOS UTILIZADOS EN EL PROCESO': 'quimicos'
    }
    df = df.rename(columns=mapeo)

    # Convertir números (manejo de comas y puntos)
    for col in ['ph', 'temp', 'sst']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    # Convertir fechas
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce').dt.date
    
    return df

# 3. CONEXIÓN Y CARGA DE DATOS
try:
    conn = st.connection("gsheets", type=GSheetsConnection)

    # BARRA LATERAL
    st.sidebar.header("Configuración de Vista")
    
    # Tabs principales
    t1, t2, t3 = st.tabs(["📊 Dashboard Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with t1:
        # Cargamos la pestaña que confirmaste: 'vertimientos'
        df_v_raw = conn.read(worksheet="vertimientos", ttl=0)
        df_v = limpiar_datos_ptar(df_v_raw)

        if not df_v.empty:
            # Filtros laterales solo para esta pestaña
            lista_procesos = sorted(df_v['proceso'].dropna().unique().tolist())
            procesos_sel = st.sidebar.multiselect("Filtrar por Proceso:", lista_procesos, default=lista_procesos)
            
            df_f = df_v[df_v['proceso'].isin(procesos_sel)]

            # Métricas
            c1, c2, c3, c4 = st.columns(4)
            val_ph = df_f['ph'].mean()
            c1.metric("Promedio pH", f"{val_ph:.2f}", delta="Óptimo" if 6<=val_ph<=9 else "Alerta")
            c2.metric("Temp. Promedio", f"{df_f['temp'].mean():.1f} °C")
            c3.metric("SST Promedio", f"{df_f['sst'].mean():.1f} mg/L")
            c4.metric("Registros", len(df_f))

            # Gráficas
            st.subheader("Análisis de Parámetros")
            fig_ph = px.line(df_f.sort_values('fecha'), x='fecha', y='ph', color='proceso', title="Tendencia de pH por Proceso")
            st.plotly_chart(fig_ph, use_container_width=True)
            
            st.subheader("Datos Recientes")
            st.dataframe(df_f, use_container_width=True)
        else:
            st.warning("No se encontraron datos en la pestaña 'vertimientos'.")

    with t2:
        st.info("Módulo de Agua Tratada en desarrollo.")

    with t3:
        st.subheader("🛠️ Estado de Maquinaria y Equipos")
        # Aquí cargamos la pestaña de mantenimiento
        # Nota: Si no la has renombrado, usa "mantenimiento" o "Form_Responses2"
        try:
            df_m = conn.read(worksheet="mantenimiento", ttl=0)
            df_m.columns = df_m.columns.str.strip()

            if not df_m.empty:
                # Mostrar Salud de Equipos en Cards
                if 'EQUIPO' in df_m.columns and 'SALUD' in df_m.columns:
                    df_resumen = df_m.drop_duplicates('EQUIPO', keep='last')
                    cols = st.columns(len(df_resumen))
                    for i, (_, row) in enumerate(df_resumen.iterrows()):
                        with cols[i]:
                            salud = str(row['SALUD']).replace('%', '')
                            st.metric(label=row['EQUIPO'], value=f"{salud}%", delta=row.get('ESTADO', ''))
                
                st.divider()
                st.write("### Historial de Intervenciones")
                st.dataframe(df_m, use_container_width=True)
            else:
                st.info("La pestaña de mantenimiento no tiene registros actuales.")
        except:
            st.error("No se pudo acceder a la pestaña de 'mantenimiento'. Verifica el nombre en el Excel.")

except Exception as e:
    st.error(f"Error General: {e}")
