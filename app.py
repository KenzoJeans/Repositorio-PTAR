import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import date

# 1. Configuración de página y Estilo
st.set_page_config(page_title="SGA - PTAR - Kenzo Jeans", layout="wide", page_icon="💧")

# --- ESTILOS PERSONALIZADOS ---
st.markdown("""
    <style>
        .block-container { padding-top: 1rem; padding-bottom: 0rem; }
        [data-testid="stImage"] img { object-fit: contain; }
        [data-testid="stSidebar"] { min-width: 320px; max-width: 350px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIÓN DE LIMPIEZA DE DATOS UNIFICADA ---
def limpiar_datos_ptar(df):
    if df is None or df.empty:
        return pd.DataFrame()
    
    df.columns = df.columns.str.strip()
    df = df.loc[:, ~df.columns.duplicated()]
    
    mapeo = {
        'ph': 'ph', 'pH': 'ph', 'PH': 'ph', 'pH Tratada': 'ph',
        'temp': 'temp', 'Temperatura': 'temp', 'Temperatura Tratada': 'temp',
        'sst': 'sst', 'SST': 'sst', 'SST Tratada': 'sst', 'Solidos suspendidos': 'sst',
        'Conductividad Tratada': 'cond', 'Caudal tratado': 'caudal',
        'Fecha': 'fecha', 'fecha': 'fecha', 'Fecha del reporte': 'fecha', 
        'Marca temporal': 'fecha_h',
        'Proceso a reportar': 'proceso'
    }
    
    df = df.rename(columns=mapeo)

    columnas_num = ['ph', 'temp', 'sst', 'cond', 'caudal']
    for col in columnas_num:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
    
    # CORRECCIÓN DE FECHAS: Normalización a objeto date para compatibilidad con filtros
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce').dt.date
    elif 'fecha_h' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha_h'], errors='coerce').dt.date
    
    return df

# --- CARGA DE DATOS ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    URL_MANTO = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=746789412#gid=746789412"
    URL_TRATADA = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=1338797542#gid=1338797542"
    URL_QUIMICOS = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=170562532#gid=170562532"

    df_base_full = limpiar_datos_ptar(conn.read(ttl=0))
    df_tratada_full = limpiar_datos_ptar(conn.read(spreadsheet=URL_TRATADA, ttl=0))
    df_manto = conn.read(spreadsheet=URL_MANTO, ttl=0)
    df_kardex = conn.read(spreadsheet=URL_QUIMICOS, ttl=0)

    # --- SIDEBAR Y FILTROS ---
    with st.sidebar:
        try:
            st.image("logo-white-kenzo.png", use_container_width=True)
        except:
            st.markdown("### KENZO JEANS")
        
        st.header("🔍 Filtros Globales")
        
        # Filtro de Procesos
        procesos = sorted(df_base_full['proceso'].unique().tolist()) if 'proceso' in df_base_full.columns else []
        sel_proceso = st.multiselect("Procesos:", procesos, default=procesos)

        # Filtro de Fechas (Afecta a todas las pestañas)
        st.subheader("📅 Rango de Tiempo")
        min_f, max_f = date(2024,1,1), date.today()
        if not df_base_full.empty:
            min_f, max_f = min(df_base_full['fecha']), max(df_base_full['fecha'])
        
        rango = st.date_input("Periodo:", [min_f, max_f])

        # Aplicación de filtros
        df_v_filt = df_base_full.copy()
        df_t_filt = df_tratada_full.copy()
        
        if len(rango) == 2:
            df_v_filt = df_v_filt[(df_v_filt['fecha'] >= rango[0]) & (df_v_filt['fecha'] <= rango[1])]
            df_t_filt = df_t_filt[(df_t_filt['fecha'] >= rango[0]) & (df_t_filt['fecha'] <= rango[1])]
        
        if sel_proceso:
            df_v_filt = df_v_filt[df_v_filt['proceso'].isin(sel_proceso)]

    # --- TABS ---
    t1, t2, t3, t4 = st.tabs(["📊 Vertimientos", "🧪 Agua tratada", "🛠️ Mantenimiento", "🧪 Químicos"])

    with t1:
        st.subheader("Monitoreo de Vertimientos")
        if not df_v_filt.empty:
            df_v_plot = df_v_filt.sort_values('fecha')
            m1, m2, m3 = st.columns(3)
            m1.metric("pH Promedio", f"{df_v_plot['ph'].mean():.2f}")
            m2.metric("Temp Promedio", f"{df_v_plot['temp'].mean():.1f} °C")
            m3.metric("SST Promedio", f"{df_v_plot['sst'].mean():.1f}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(px.line(df_v_plot, x='fecha', y='ph', markers=True, title="Histórico pH", template="plotly_dark"), use_container_width=True)
            with col2:
                df_bar = df_v_plot.groupby('proceso')['ph'].mean().reset_index()
                st.plotly_chart(px.bar(df_bar, x='proceso', y='ph', color='proceso', title="pH por Proceso", template="plotly_dark"), use_container_width=True)
        else:
            st.warning("No hay datos en el rango seleccionado.")

    with t2:
        st.subheader("Análisis de Agua Tratada")
        if not df_t_filt.empty:
            df_t_plot = df_t_filt.sort_values('fecha')
            sst_ent = df_base_full['sst'].mean() if not df_base_full.empty else 1
            rem = (1 - (df_t_plot['sst'].mean() / sst_ent)) * 100
            
            c1, c2 = st.columns(2)
            c1.metric("Eficiencia de Remoción", f"{rem:.1f}%")
            c2.metric("Caudal Total", f"{df_t_plot['caudal'].sum():.1f} m³")
            
            st.plotly_chart(px.area(df_t_plot, x='fecha', y='temp', title="Temperatura Salida", color_discrete_sequence=['#FFA726'], template="plotly_dark"), use_container_width=True)
            st.plotly_chart(px.bar(df_t_plot, x='fecha', y='caudal', title="Caudal Diario", template="plotly_dark"), use_container_width=True)
        else:
            st.info("Sin datos de agua tratada en este periodo.")

    with t3:
        st.subheader("🛠️ Estado de Equipos - Kenzo Jeans")
        if not df_manto.empty:
            df_manto.columns = df_manto.columns.str.strip().str.upper()
            if 'SALUD' in df_manto.columns:
                df_manto['SALUD'] = pd.to_numeric(df_manto['SALUD'], errors='coerce').fillna(0)
            
            col_fecha_m = 'FECHA' if 'FECHA' in df_manto.columns else df_manto.columns[0]
            equipos = df_manto['EQUIPO'].unique() if 'EQUIPO' in df_manto.columns else []
            
            # Tarjetas de Salud
            cols_eq = st.columns(3)
            for i, eq in enumerate(equipos[:6]): # Limite a 6 para vista rápida
                ult = df_manto[df_manto['EQUIPO'] == eq].iloc[-1]
                val = ult['SALUD']
                color = "#4CAF50" if val >= 8 else "#FFEB3B" if val >= 6 else "#F44336"
                with cols_eq[i % 3]:
                    st.markdown(f"""<div style="background:#1E1E1E; padding:15px; border-radius:10px; border-left:8px solid {color}; margin-bottom:10px;">
                        <h5 style="margin:0;">{eq}</h5><h2 style="margin:5px 0;">{val}/10</h2></div>""", unsafe_allow_html=True)
            
            # Heatmap
            st.write("**Mapa de Salud Histórico**")
            df_pivot = df_manto.pivot_table(index='EQUIPO', columns=col_fecha_m, values='SALUD', aggfunc='last').fillna(0)
            st.plotly_chart(px.imshow(df_pivot, color_continuous_scale='RdYlGn', template="plotly_dark"), use_container_width=True)
        else:
            st.warning("No hay datos de mantenimiento.")

    with t4:
        st.subheader("📦 Inventario de Químicos")
        STOCK_INI = {"SULFATO DE ALUMINIO": 119, "CAL": 79, "POLIMERO": 24.118}
        if not df_kardex.empty:
            df_kardex.columns = df_kardex.columns.str.strip().str.upper()
            df_kardex['CANTIDAD'] = pd.to_numeric(df_kardex['CANTIDAD'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
            
            # Lógica de Stock
            df_kardex['NETO'] = df_kardex.apply(lambda x: x['CANTIDAD'] if x['QUE PROCESO VA A REALIZAR'] == 'ENTRADA' else -x['CANTIDAD'], axis=1)
            resumen = df_kardex.groupby('NOMBRE DEL QUIMICO')['NETO'].sum().to_dict()
            
            ck = st.columns(3)
            for i, (prod, ini) in enumerate(STOCK_INI.items()):
                actual = ini + resumen.get(prod, 0)
                ck[i].metric(prod, f"{actual:.1f} kg", delta="Bajo" if actual < 20 else "OK", delta_color="inverse" if actual < 20 else "normal")
            
            st.write("**Historial de Movimientos**")
            st.dataframe(df_kardex[['FECHA', 'NOMBRE DEL QUIMICO', 'QUE PROCESO VA A REALIZAR', 'CANTIDAD']], use_container_width=True)

except Exception as e:
    st.error(f"Error en la aplicación: {e}")
