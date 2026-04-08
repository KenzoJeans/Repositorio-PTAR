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
# Sugerencia: Si tienes una pestaña específica para químicos, agrega su URL/GID aquí
URL_DIRECTA_QUIMICOS = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=TU_GID_AQUI"

# 2. Función de limpieza de datos UNIFICADA
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

# 3. Carga de Datos Principal
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Dataset 1: Vertimientos (Base)
    df_raw = conn.read(ttl=0) 
    df_base_full = limpiar_datos_ptar(df_raw)

    # Dataset 2: Agua Tratada
    try:
        df_tratada = limpiar_datos_ptar(conn.read(spreadsheet=URL_DIRECTA_TRATADA, ttl=0))
    except:
        df_tratada = pd.DataFrame()

    # Dataset 3: Mantenimiento
    try:
        df_manto = conn.read(spreadsheet=URL_DIRECTA_MANTO, ttl=0)
        df_manto.columns = df_manto.columns.str.strip()
    except:
        df_manto = pd.DataFrame()

    # --- BARRA LATERAL ---
    st.sidebar.header("Filtros Dashboard Vertimientos")
    df_vert_filtrado = df_base_full.copy()

    if not df_base_full.empty and 'fecha' in df_base_full.columns:
        min_f, max_f = min(df_base_full['fecha']), max(df_base_full['fecha'])
        rango = st.sidebar.date_input("Rango de fechas:", [min_f, max_f])
        if len(rango) == 2:
            df_vert_filtrado = df_vert_filtrado[(df_vert_filtrado['fecha'] >= rango[0]) & (df_vert_filtrado['fecha'] <= rango[1])]

    if not df_base_full.empty and 'proceso' in df_base_full.columns:
        procesos = sorted(df_base_full['proceso'].unique().tolist())
        sel = st.sidebar.multiselect("Procesos:", procesos, default=procesos)
        df_vert_filtrado = df_vert_filtrado[df_vert_filtrado['proceso'].isin(sel)]

    # --- TABS (Agregamos la pestaña 4) ---
    t1, t2, t3, t4 = st.tabs(["📊 Dashboard Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento", "🧪 Consumo Químicos"])

    with t1:
        # (Se mantiene igual a tu código original)
        if not df_vert_filtrado.empty:
            m1, m2, m3, m4 = st.columns(4)
            avg_ph, avg_temp, avg_sst = df_vert_filtrado['ph'].mean(), df_vert_filtrado['temp'].mean(), df_vert_filtrado['sst'].mean()
            m1.metric("Promedio pH", f"{avg_ph:.2f}", delta="NORMA" if 6<=avg_ph<=9 else "ALERTA")
            m2.metric("Temp Promedio", f"{avg_temp:.1f} °C", delta="NORMAL" if avg_temp<=40 else "ALTA")
            m3.metric("SST Promedio", f"{avg_sst:.1f} mg/L")
            m4.metric("Registros", len(df_vert_filtrado))
            st.subheader("📈 Histórico de pH (Entrada)")
            st.plotly_chart(px.line(df_vert_filtrado.sort_values('fecha'), x='fecha', y='ph', markers=True, template="plotly_dark"), use_container_width=True)
            col_a, col_b = st.columns(2)
            with col_a:
                st.write("**SST por Proceso**")
                st.plotly_chart(px.bar(df_vert_filtrado.groupby('proceso')['sst'].mean().reset_index(), x='proceso', y='sst', template="plotly_dark"), use_container_width=True)
            with col_b:
                st.write("**Temperatura por Proceso**")
                st.plotly_chart(px.line(df_vert_filtrado.groupby('proceso')['temp'].mean().reset_index(), x='proceso', y='temp', markers=True, template="plotly_dark"), use_container_width=True)
        else:
            st.warning("Ajusta los filtros para ver datos de Vertimientos.")

    with t2:
        # (Se mantiene igual a tu código original)
        st.subheader("🧪 Monitoreo de Agua Tratada (Salida)")
        if not df_tratada.empty:
            avg_sst_sal = df_tratada['sst'].mean()
            sst_ent = df_base_full['sst'].mean() if not df_base_full.empty else 1
            rem = 100.0 if avg_sst_sal == 0 else ((sst_ent - avg_sst_sal) / sst_ent) * 100
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("SST Salida", f"{avg_sst_sal:.1f} mg/L", delta=f"{rem:.1f}% Remoción")
            c2.metric("pH Promedio", f"{df_tratada['ph'].mean():.2f}", delta="OK" if 6<=df_tratada['ph'].mean()<=9 else "REVISAR")
            c3.metric("Temp Salida", f"{df_tratada['temp'].mean():.1f} °C", delta="OK" if df_tratada['temp'].mean()<=40 else "ALTA")
            c4.metric("Caudal Total", f"{df_tratada['caudal'].sum():.1f} m³")
            st.markdown("---")
            cola, colb = st.columns(2)
            with cola:
                st.plotly_chart(px.line(df_tratada.sort_values('fecha'), x='fecha', y=['ph', 'temp'], title="pH vs Temperatura (Tratada)", template="plotly_dark"), use_container_width=True)
            with colb:
                st.plotly_chart(px.area(df_tratada.sort_values('fecha'), x='fecha', y='cond', title="Conductividad (µS/cm)", template="plotly_dark", color_discrete_sequence=['#00CC96']), use_container_width=True)
            st.plotly_chart(px.bar(df_tratada.sort_values('fecha'), x='fecha', y='caudal', title="Caudal Diario (m³)", template="plotly_dark"), use_container_width=True)
        else:
            st.info("Cargue datos en la pestaña de Agua Tratada.")

    with t3:
        # (Se mantiene igual a tu código original)
        st.subheader("🛠️ Estado de Equipos")
        if not df_manto.empty:
            if 'SALUD' in df_manto.columns:
                df_manto['SALUD'] = pd.to_numeric(df_manto['SALUD'], errors='coerce').fillna(0)
            equipos = df_manto['EQUIPO'].unique() if 'EQUIPO' in df_manto.columns else []
            cols_eq = st.columns(3)
            for i, eq in enumerate(equipos):
                ult = df_manto[df_manto['EQUIPO'] == eq].iloc[-1]
                val_s = ult['SALUD']
                color = "#4CAF50" if val_s >= 8 else "#FFEB3B" if val_s >= 6 else "#F44336"
                with cols_eq[i % 3]:
                    st.markdown(f"""<div style="background:#1E1E1E; padding:15px; border-radius:10px; border-top:5px solid {color}; margin-bottom:10px;">
                        <h4 style="margin:0;">⚙️ {eq}</h4>
                        <p style="color:{color}; margin:0;">Salud: {val_s}/10</p>
                        <small style="color:#888;">Prox: {ult.get('FECHA PROX MANTENIMIENTO', 'N/A')}</small>
                    </div>""", unsafe_allow_html=True)
            with st.expander("Historial"):
                st.dataframe(df_manto, use_container_width=True)

    with t4:
        st.subheader("🧪 Reporte de Consumo de Químicos")
        # Usamos df_raw (la hoja principal) que suele tener la columna de químicos
        if not df_base_full.empty and 'quimicos' in df_base_full.columns:
            # Filtro rápido de texto para químicos
            q_search = st.text_input("Buscar químico específico:", "")
            df_q = df_base_full.copy()
            if q_search:
                df_q = df_q[df_q['quimicos'].str.contains(q_search, case=False, na=False)]
            
            # Gráfica de uso por proceso
            fig_q = px.sunburst(df_q, path=['proceso', 'quimicos'], title="Distribución de Químicos por Etapa", template="plotly_dark")
            st.plotly_chart(fig_q, use_container_width=True)
            
            st.markdown("### Listado Detallado de Consumos")
            st.dataframe(df_q[['fecha', 'proceso', 'quimicos']], use_container_width=True)
        else:
            st.info("No se detectó la columna 'Productos quimicos utilizados en el proceso' en la base de datos.")

except Exception as e:
    st.error(f"Error: {e}")
