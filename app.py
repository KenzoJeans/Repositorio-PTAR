import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# CONFIGURACIÓN
st.set_page_config(page_title="Control de Vertimientos PTAR", layout="wide")
st.title("💧 Control de Parámetros de Vertimientos Diarios")
st.markdown("Análisis de pH, Temperatura, Conductividad y Sólidos")

# 1. SIMULACIÓN DE DATOS REPRODUCIBLES (Para que veas el ejemplo ya mismo)
@st.cache_data
def generar_datos_ptar():
    fechas = pd.date_range(start="2024-01-01", periods=90, freq='D')
    procesos = ['Entrada', 'Reactor Bio', 'Sedimentador', 'Salida Final']
    lista_datos = []
    
    for fecha in fechas:
        for proc in procesos:
            lista_datos.append({
                'Fecha': fecha,
                'Proceso': proc,
                'pH': np.random.uniform(6.5, 8.5),
                'Temp_C': np.random.uniform(18, 25),
                'Conductividad': np.random.uniform(400, 800),
                'Solidos_Sed_ml_L': np.random.uniform(0.1, 1.5)
            })
    return pd.DataFrame(lista_datos)

df = generar_datos_ptar()
df['Mes'] = df['Fecha'].dt.strftime('%B %Y')

# 2. FILTROS LATERALES
st.sidebar.header("Configuración del Informe")
proceso_sel = st.sidebar.selectbox("Selecciona el Proceso:", df['Proceso'].unique())
mes_sel = st.sidebar.multiselect("Filtrar por Mes:", options=df['Mes'].unique(), default=df['Mes'].unique())

# Aplicar filtros
mask = (df['Proceso'] == proceso_sel) & (df['Mes'].isin(mes_sel))
df_filtrado = df[mask]

# 3. KPIs DE PROMEDIOS MENSUALES
st.subheader(f"Resumen de Promedios: {proceso_sel}")
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric("pH Promedio", f"{df_filtrado['pH'].mean():.2f}")
with c2:
    st.metric("Temp. Media (°C)", f"{df_filtrado['Temp_C'].mean():.1f}")
with c3:
    st.metric("Conductividad Prom.", f"{df_filtrado['Conductividad'].mean():.0f} µS/cm")
with c4:
    st.metric("Sólidos Prom.", f"{df_filtrado['Solidos_Sed_ml_L'].mean():.2f} ml/L")

st.divider()

# 4. GRÁFICOS DE VARIACIÓN (Tendencia Diaria)
st.subheader("Variación Diaria de Parámetros")
tab1, tab2 = st.tabs(["pH y Temperatura", "Conductividad y Sólidos"])

with tab1:
    fig_ph = px.line(df_filtrado, x='Fecha', y=['pH', 'Temp_C'], 
                     title=f"Evolución de pH y Temperatura en {proceso_sel}",
                     labels={'value': 'Escala', 'variable': 'Parámetro'},
                     template="plotly_white")
    st.plotly_chart(fig_ph, use_container_width=True)

with tab2:
    fig_cond = px.scatter(df_filtrado, x='Fecha', y='Conductividad', 
                          size='Solidos_Sed_ml_L', color='Solidos_Sed_ml_L',
                          title="Conductividad vs Sólidos Sedimentables",
                          labels={'Conductividad': 'Conductividad (µS/cm)'},
                          template="plotly_white")
    st.plotly_chart(fig_cond, use_container_width=True)

# 5. TABLA DE DATOS PARA EL INFORME
with st.expander("Ver Datos Detallados del Mes"):
    st.write(df_filtrado.sort_values('Fecha', ascending=False))
