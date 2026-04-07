import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 1. Configuración de página y Estilo
st.set_page_config(page_title="Sistema Control PTAR", layout="wide", page_icon="💧")
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)
st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# --- CONFIGURACIÓN DE CONEXIÓN ---
URL_DIRECTA_MANTO = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=746789412#gid=746789412" 
URL_DIRECTA_TRATADA = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=1338797542#gid=1338797542"

# 2. Función de limpieza de datos REFORZADA
def limpiar_datos_ptar(df):
    if df is None or df.empty:
        return pd.DataFrame()
    
    df.columns = df.columns.str.strip()
    df = df.loc[:, ~df.columns.duplicated()] # Blindaje contra duplicate keys
    
    mapeo = {
        'ph': 'ph', 'pH': 'ph', 'pH Tratada': 'ph',
        'temp': 'temp', 'Temperatura': 'temp', 'Temperatura Tratada': 'temp',
        'sst': 'sst', 'SST': 'sst', 'SST Tratada': 'sst',
        'Conductividad Tratada': 'cond', 'Caudal tratado': 'caudal',
        'Fecha': 'fecha', 'Marca temporal': 'fecha_h',
        'Proceso a reportar': 'proceso'
    }
    
    nuevos_nombres = {}
    for col in df.columns:
        if col in mapeo:
            target = mapeo[col]
            if target not in nuevos_nombres.values():
                nuevos_nombres[col] = target
    
    df = df.rename(columns=nuevos_nombres)

    columnas_num = ['ph', 'temp', 'sst', 'cond', 'caudal']
    for col in columnas_num:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        else:
            df[col] = 0.0
    
    if 'fecha' not in df.columns and 'fecha_h' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha_h'], errors='coerce').dt.date
    elif 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce').dt.date
    
    return df

# 3. Carga de Datos
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_base = limpiar_datos_ptar(conn.read(ttl=0))

    try:
        df_tratada = limpiar_datos_ptar(conn.read(spreadsheet=URL_DIRECTA_TRATADA, ttl=0))
    except:
        df_tratada = pd.DataFrame()

    try:
        df_manto = conn.read(spreadsheet=URL_DIRECTA_MANTO, ttl=0)
        df_manto.columns = df_manto.columns.str.strip()
    except:
        df_manto = pd.DataFrame()

    # --- TABS ---
    t1, t2, t3 = st.tabs(["📊 Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with t1:
        if not df_base.empty:
            st.subheader("Análisis de Entrada")
            m1, m2 = st.columns(2)
            m1.metric("pH Promedio Entrada", f"{df_base['ph'].mean():.2f}")
            m2.metric("SST Promedio Entrada", f"{df_base['sst'].mean():.2f}")
            st.plotly_chart(px.line(df_base.sort_values('fecha'), x='fecha', y='ph', title="Histórico pH Entrada", template="plotly_dark"), use_container_width=True)

    with t2:
        st.subheader("🧪 Monitoreo de Agua Tratada (Salida)")
        if not df_tratada.empty:
            # Cálculos de promedios
            avg_sst_sal = df_tratada['sst'].mean()
            avg_ph_sal = df_tratada['ph'].mean()
            avg_temp_sal = df_tratada['temp'].mean()
            
            # Lógica de Remoción SST
            if avg_sst_sal == 0:
                texto_remocion = "100% Remoción"
                color_remocion = "normal"
            else:
                sst_ent = df_base['sst'].mean() if not df_base.empty else 0
                rem = ((sst_ent - avg_sst_sal) / sst_ent) * 100 if sst_ent > 0 else 0
                texto_remocion = f"{rem:.1f}% Remoción"
                color_remocion = "normal" if rem > 80 else "inverse"

            # Columnas de Métricas con Indicadores (Deltas)
            c1, c2, c3, c4 = st.columns(4)
            
            c1.metric("SST Salida", f"{avg_sst_sal:.1f} mg/L", 
                      delta=texto_remocion, delta_color=color_remocion)
            
            c2.metric("pH Promedio", f"{avg_ph_sal:.2f}", 
                      delta="DENTRO DE NORMA" if 6.0 <= avg_ph_sal <= 9.0 else "FUERA DE RANGO",
                      delta_color="normal" if 6.0 <= avg_ph_sal <= 9.0 else "inverse")
            
            c3.metric("Temp. Promedio", f"{avg_temp_sal:.1f} °C", 
                      delta="NORMAL" if avg_temp_sal <= 40 else "ALTA",
                      delta_color="normal" if avg_temp_sal <= 40 else "inverse")
            
            c4.metric("Caudal Total", f"{df_tratada['caudal'].sum():.1f} m³")

            # Gráficas
            st.markdown("---")
            col_left, col_right = st.columns(2)
            with col_left:
                fig_criticas = px.line(df_tratada.sort_values('fecha'), x='fecha', y=['ph', 'temp'], 
                                       markers=True, title="Tendencia pH vs Temperatura", template="plotly_dark")
                st.plotly_chart(fig_criticas, use_container_width=True)
            with col_right:
                fig_cond = px.area(df_tratada.sort_values('fecha'), x='fecha', y='cond', 
                                   title="Conductividad (µS/cm)", template="plotly_dark", color_discrete_sequence=['#00CC96'])
                st.plotly_chart(fig_cond, use_container_width=True)

            st.markdown("---")
            st.plotly_chart(px.bar(df_tratada.sort_values('fecha'), x='fecha', y='caudal', 
                                title="Volumen Tratado (m³)", template="plotly_dark", color='caudal'), use_container_width=True)
        else:
            st.info("No hay datos en Agua Tratada.")

    with t3:
        if not df_manto.empty:
            st.subheader("Panel de Equipos")
            st.dataframe(df_manto, use_container_width=True)

except Exception as e:
    st.error(f"Error en la aplicación: {e}")
