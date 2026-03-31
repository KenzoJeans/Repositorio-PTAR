import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Dashboard Ejecutivo Gémini", layout="wide")

# Título y estilo
st.title("📊 Dashboard de Rendimiento Empresarial")
st.markdown("Generado automáticamente con **Python + Streamlit**")
st.divider()

# 2. GENERACIÓN DE DATOS (Simulación)
@st.cache_data # Esto hace que la app sea rápida y no recargue datos innecesariamente
def cargar_datos():
    np.random.seed(42)
    fechas = pd.date_range(start="2023-01-01", end="2023-12-31", freq='D')
    n_dias = len(fechas)
    df = pd.DataFrame({
        'Fecha': fechas,
        'Ventas': np.random.uniform(1000, 5000, n_dias) + np.sin(np.linspace(0, 4*np.pi, n_dias))*500,
        'Costos': np.random.uniform(500, 3000, n_dias),
        'Region': np.random.choice(['Norte', 'Sur', 'Este', 'Oeste'], n_dias),
        'Producto': np.random.choice(['Software Plan A', 'Software Plan B', 'Soporte Premium'], n_dias),
        'Satisfaccion': np.random.uniform(3.5, 5.0, n_dias)
    })
    df['Ganancia'] = df['Ventas'] - df['Costos']
    df['Mes'] = df['Fecha'].dt.strftime('%B')
    return df

df = cargar_datos()

# 3. FILTROS EN LA BARRA LATERAL (Sidebar)
st.sidebar.header("Filtros de Informe")
region_sel = st.sidebar.multiselect("Selecciona Región:", 
                                    options=df["Region"].unique(), 
                                    default=df["Region"].unique())

# Filtrar el dataframe basado en la selección
df_filtrado = df[df["Region"].isin(region_sel)]

# 4. KPIs PRINCIPALES (Métricas en columnas)
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Ventas", f"${df_filtrado['Ventas'].sum():,.0f}", "+12%")
with col2:
    st.metric("Ganancia Neta", f"${df_filtrado['Ganancia'].sum():,.0f}", "5%")
with col3:
    st.metric("Margen Promedio", f"{(df_filtrado['Ganancia'].sum()/df_filtrado['Ventas'].sum())*100:.1f}%")
with col4:
    st.metric("Satisfacción", f"{df_filtrado['Satisfaccion'].mean():.2f} / 5", "⭐")

st.divider()

# 5. GRÁFICOS INTERACTIVOS
col_izq, col_der = st.columns(2)

with col_izq:
    # Tendencia Mensual
    df_mensual = df_filtrado.groupby(df_filtrado['Fecha'].dt.month)['Ventas'].sum().reset_index()
    fig_linea = px.line(df_mensual, x='Fecha', y='Ventas', 
                        title="Evolución de Ventas por Mes",
                        markers=True, template="plotly_white")
    st.plotly_chart(fig_linea, use_container_width=True)

with col_der:
    # Ventas por Producto
    fig_barras = px.bar(df_filtrado, x="Producto", y="Ventas", 
                         color="Producto", title="Ventas por Categoría",
                         template="plotly_white")
    st.plotly_chart(fig_barras, use_container_width=True)

# 6. TABLA DE DATOS (Opcional)
with st.expander("Ver base de datos completa"):
    st.dataframe(df_filtrado)
