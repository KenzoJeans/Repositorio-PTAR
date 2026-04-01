import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Configuración de página
st.set_page_config(page_title="Gestión PTAR Pro", layout="wide", page_icon="💧")

st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# 2. Conexión a Google Sheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # CARGA GLOBAL: Traemos la hoja principal (que es la que sabemos que funciona)
    # y la usamos como base de datos maestra.
    df_maestro = conn.read(ttl=0)
    
    # 3. Limpieza de datos estándar
    def limpiar_ptar(df):
        if df is None or df.empty: return pd.DataFrame()
        df.columns = df.columns.str.strip()
        
        # Mapeo de columnas para métricas (basado en lo que ya funciona)
        mapeo = {'ph': 'ph', 'pH': 'ph', 'temp': 'temp', 'Temperatura': 'temp', 'sst': 'sst'}
        df = df.rename(columns={k: v for k, v in mapeo.items() if k in df.columns})
        
        # Asegurar números (para que no salga el error de 'mean' con strings)
        for c in ['ph', 'temp', 'sst']:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.'), errors='coerce')
        return df

    # --- INTERFAZ DE PESTAÑAS ---
    t1, t2, t3 = st.tabs(["📊 Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with t1:
        df_v = limpiar_ptar(df_maestro)
        
        if not df_v.empty:
            # Filtros laterales o superiores
            procesos = df_v['Proceso a reportar'].unique().tolist() if 'Proceso a reportar' in df_v.columns else []
            if procesos:
                sel = st.multiselect("Filtrar por Proceso:", procesos, default=procesos)
                df_v = df_v[df_v['Proceso a reportar'].isin(sel)]

            # Métricas Profesionales
            m1, m2, m3 = st.columns(3)
            m1.metric("Promedio pH", f"{df_v['ph'].mean():.2f}")
            m2.metric("Temp Promedio", f"{df_v['temp'].mean():.1f} °C")
            m3.metric("Total Registros", len(df_v))

            st.subheader("Visualización de Datos Actualizados")
            st.dataframe(df_v, use_container_width=True)
            
            # Gráfica de tendencia simple
            if 'ph' in df_v.columns:
                st.line_chart(df_v['ph'])
        else:
            st.error("No se detectan datos en la hoja principal.")

    with t2:
        st.info("Pestaña configurada. Para visualizar datos de Agua Tratada, "
                "asegúrate de que estén en la hoja principal o en una tabla identificable.")

    with t3:
        st.info("Mantenimiento de equipos: Sección lista para integración de bitácora.")

except Exception as e:
    st.error(f"Error de sistema: {e}")
