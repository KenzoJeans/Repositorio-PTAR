import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 1. Configuración de página y Estilo
st.set_page_config(page_title="SGA - PTAR - Kenzo Jeans", layout="wide", page_icon="💧")
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)

# --- ENCABEZADO PERSONALIZADO KENZO JEANS SAS ---
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
        }
        [data-testid="stImage"] img {
            object-fit: contain;
        }
    </style>
    """, unsafe_allow_html=True)

col_logo, col_titulo = st.columns([1.2, 5])

with col_logo:
    try:
        st.image("logo-white-kenzo.png", use_container_width=True)
    except Exception:
        st.markdown("**KENZO JEANS**")

with col_titulo:
    st.title("SGA - Gestión Integral PTAR - Kenzo Jeans SAS")

# --- CONFIGURACIÓN DE CONEXIÓN ---
URL_DIRECTA_MANTO = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=746789412#gid=746789412"
URL_DIRECTA_TRATADA = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=1338797542#gid=1338797542"
URL_DIRECTA_QUIMICOS = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=170562532#gid=170562532"

# 2. Función de limpieza de datos AJUSTADA (Fechas corregidas)
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
    
    nuevos_nombres = {col: mapeo[col] for col in df.columns if col in mapeo}
    df = df.rename(columns=nuevos_nombres)

    columnas_num = ['ph', 'temp', 'sst', 'cond', 'caudal']
    for col in columnas_num:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
    
    # --- AJUSTE DE FECHAS PARA EVITAR ERROR DE MESES ---
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
    elif 'fecha_h' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha_h'], errors='coerce')
    
    df = df.dropna(subset=['fecha'])
    return df

# 3. Carga de Datos Principal
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_raw = conn.read(ttl=0) 
    df_base_full = limpiar_datos_ptar(df_raw)

    try:
        df_tratada = limpiar_datos_ptar(conn.read(spreadsheet=URL_DIRECTA_TRATADA, ttl=0))
    except:
        df_tratada = pd.DataFrame()

    try:
        df_manto = conn.read(spreadsheet=URL_DIRECTA_MANTO, ttl=0)
        df_manto.columns = df_manto.columns.str.strip()
    except:
        df_manto = pd.DataFrame()

    try:
        df_kardex = conn.read(spreadsheet=URL_DIRECTA_QUIMICOS, ttl=0)
    except:
        df_kardex = pd.DataFrame()

    st.markdown("""<style>[data-testid="stSidebar"] { min-width: 320px; max-width: 350px; }</style>""", unsafe_allow_html=True)

    with st.sidebar:
        try:
            st.image("logo-white-kenzo.png", use_container_width=True)
            st.markdown("---")
        except Exception:
            pass

        st.header("🔍 Filtros Dashboard")
        df_vert_filtrado = df_base_full.copy()

        if not df_base_full.empty and 'proceso' in df_base_full.columns:
            procesos = sorted(df_base_full['proceso'].unique().tolist())
            sel = st.multiselect("Seleccionar Procesos:", procesos, default=procesos)
            df_vert_filtrado = df_vert_filtrado[df_vert_filtrado['proceso'].isin(sel)]

        filtro_q = st.text_input("Filtrar por Químico:", "")
        if filtro_q and 'quimico' in df_vert_filtrado.columns:
            df_vert_filtrado = df_vert_filtrado[df_vert_filtrado['quimico'].astype(str).str.contains(filtro_q, case=False, na=False)]

        st.markdown("---")
        
        # --- FILTRO DE FECHAS CORREGIDO ---
        if not df_base_full.empty and 'fecha' in df_base_full.columns:
            st.subheader("📅 Rango de Tiempo")
            min_f, max_f = df_base_full['fecha'].min(), df_base_full['fecha'].max()
            rango = st.date_input("Seleccionar fechas:", [min_f, max_f], key="sidebar_date_range")
            
            if isinstance(rango, list) and len(rango) == 2:
                start_date = pd.to_datetime(rango[0])
                end_date = pd.to_datetime(rango[1])
                df_vert_filtrado = df_vert_filtrado[(df_vert_filtrado['fecha'] >= start_date) & 
                                                    (df_vert_filtrado['fecha'] <= end_date)]

    t1, t2, t3, t4 = st.tabs(["📊 Dashboard de vertimientos", "🧪 Agua tratada", "🛠️ Mantenimiento", "🧪 Consumo de químicos"])

    with t1:
        if not df_vert_filtrado.empty:
            m1, m2, m3, m4 = st.columns(4)
            avg_ph = df_vert_filtrado['ph'].mean()
            avg_temp = df_vert_filtrado['temp'].mean()
            avg_sst = df_vert_filtrado['sst'].mean()
            
            m1.metric("Promedio pH", f"{avg_ph:.2f}", delta="NORMA" if 6<=avg_ph<=9 else "ALERTA", delta_color="normal" if 6<=avg_ph<=9 else "inverse")
            m2.metric("Temp Promedio", f"{avg_temp:.1f} °C", delta="NORMAL" if avg_temp<=40 else "ALTA", delta_color="normal" if avg_temp<=40 else "inverse")
            m3.metric("SST Promedio", f"{avg_sst:.1f} mg/L")
            m4.metric("Registros", len(df_vert_filtrado))

            st.markdown("---")

            col1, col2 = st.columns(2)
            with col1:
                st.write("**📈 Histórico de pH (Tintorería)**")
                fig_ph = px.line(df_vert_filtrado.sort_values('fecha'), x='fecha', y='ph', markers=True, template="plotly_dark")
                fig_ph.update_xaxes(type='date')
                st.plotly_chart(fig_ph, use_container_width=True)
            with col2:
                st.write("**📊 pH por proceso**")
                df_ph_p = df_vert_filtrado.groupby('proceso')['ph'].mean().reset_index()
                st.plotly_chart(px.bar(df_ph_p, x='proceso', y='ph', color='proceso', template="plotly_dark"), use_container_width=True)

            col3, col4 = st.columns(2)
            with col3:
                st.markdown("<h4 style='text-align: center; color: #FFA726;'>🌡️ Tendencia de temperatura promedio</h4>", unsafe_allow_html=True)
                fig_temp_hist = px.area(df_vert_filtrado.sort_values('fecha'), x='fecha', y='temp', template="plotly_dark", color_discrete_sequence=['#FF9800'])
                fig_temp_hist.update_xaxes(type='date')
                fig_temp_hist.update_traces(fillcolor="rgba(255, 152, 0, 0.4)", line=dict(color="#FFB74D", width=2))
                st.plotly_chart(fig_temp_hist, use_container_width=True)
                
            with col4:
                st.markdown("<h4 style='text-align: center; color: #FFD54F;'>📊 Temperatura por proceso</h4>", unsafe_allow_html=True)
                df_temp_proc = df_vert_filtrado.groupby('proceso')['temp'].mean().reset_index()
                fig_temp_proc = px.line(df_temp_proc, x='proceso', y='temp', markers=True, template="plotly_dark", color_discrete_sequence=['#FFD54F'])
                st.plotly_chart(fig_temp_proc, use_container_width=True)

            st.write("**🍩 Promedio de Sólidos (SST) por proceso**")
            df_sst_p = df_vert_filtrado.groupby('proceso')['sst'].mean().reset_index()
            st.plotly_chart(px.pie(df_sst_p, values='sst', names='proceso', hole=0.5, template="plotly_dark"), use_container_width=True)
            
            st.write("**📄 Tabla de Datos**")
            st.dataframe(df_vert_filtrado, use_container_width=True)
        else:
            st.warning("Ajusta los filtros para ver datos.")

    with t2:
        st.subheader("🧪 Monitoreo de Agua Tratada")
        if not df_tratada.empty:
            avg_sst_sal = df_tratada['sst'].mean()
            sst_ent = df_base_full['sst'].mean() if not df_base_full.empty else 1
            remocion = 100.0 if avg_sst_sal == 0 else max(0, (1 - (avg_sst_sal / sst_ent)) * 100)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("SST Salida (Prom)", f"{avg_sst_sal:.1f} mg/L", delta=f"{remocion:.1f}% Eficiencia")
            c2.metric("pH Salida", f"{df_tratada['ph'].mean():.2f}", delta="OK" if 6<=df_tratada['ph'].mean()<=9 else "FUERA")
            c3.metric("Temp Salida", f"{df_tratada['temp'].mean():.1f} °C", delta="ESTABLE" if df_tratada['temp'].mean()<=40 else "ALTA")
            c4.metric("Caudal Total", f"{df_tratada['caudal'].sum():.1f} m³")

            st.markdown("---")

            col_a, col_b = st.columns(2)
            with col_a:
                st.write("**📈 pH del Agua Tratada (Tiempo)**")
                fig_ph_t = px.line(df_tratada.sort_values('fecha'), x='fecha', y='ph', markers=True, template="plotly_dark", color_discrete_sequence=['#00C853'])
                fig_ph_t.update_xaxes(type='date')
                fig_ph_t.add_hline(y=6, line_dash="dash", line_color="red")
                fig_ph_t.add_hline(y=9, line_dash="dash", line_color="red")
                st.plotly_chart(fig_ph_t, use_container_width=True)

            with col_b:
                st.write("**🌡️ Temperatura de Salida (Tiempo)**")
                fig_temp_t = px.area(df_tratada.sort_values('fecha'), x='fecha', y='temp', template="plotly_dark", color_discrete_sequence=['#FFA726'])
                fig_temp_t.update_xaxes(type='date')
                st.plotly_chart(fig_temp_t, use_container_width=True)
        else:
            st.warning("No hay datos en 'Agua Tratada'.")

    # [Pestañas t3 y t4 permanecen igual que tu original con los cierres correctos]
    with t3:
        st.subheader("🛠️ Estado de Equipos - Kenzo Jeans")
        if not df_manto.empty:
            df_manto.columns = df_manto.columns.str.strip().str.upper()
            if 'SALUD' in df_manto.columns:
                df_manto['SALUD'] = pd.to_numeric(df_manto['SALUD'], errors='coerce').fillna(0)
            col_fecha_m = 'FECHA' if 'FECHA' in df_manto.columns else df_manto.columns[0]
            if 'EQUIPO' in df_manto.columns:
                equipos = df_manto['EQUIPO'].unique()
                cols_eq = st.columns(3)
                for i, eq in enumerate(equipos):
                    ult_reg = df_manto[df_manto['EQUIPO'] == eq].iloc[-1]
                    val_s = ult_reg['SALUD']
                    color = "#4CAF50" if val_s >= 8 else "#FFEB3B" if val_s >= 6 else "#F44336"
                    with cols_eq[i % 3]:
                        st.markdown(f'<div style="background:#1E1E1E; padding:20px; border-radius:15px; border-left:10px solid {color}; margin-bottom:20px;"><h4>{eq}</h4><h2>📈 {val_s}/10</h2></div>', unsafe_allow_html=True)

    with t4:
        st.subheader("📦 Gestión de Inventarios y Consumo")
        STOCK_INICIAL = {"SULFATO DE ALUMINIO": 119, "CAL": 79, "POLIMERO": 24.118}
        if not df_kardex.empty:
            df_kardex.columns = df_kardex.columns.str.strip().str.upper()
            df_kardex['CANTIDAD'] = pd.to_numeric(df_kardex['CANTIDAD'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
            df_kardex['FECHA'] = pd.to_datetime(df_kardex['FECHA'], errors='coerce')
            
            # Cálculo de Inventario
            df_kardex['NETO'] = df_kardex.apply(lambda x: x['CANTIDAD'] if x['QUE PROCESO VA A REALIZAR'] == 'ENTRADA' else -x['CANTIDAD'], axis=1)
            resumen_inv = df_kardex.groupby('NOMBRE DEL QUIMICO')['NETO'].sum().to_dict()
            ck1, ck2, ck3 = st.columns(3)
            for i, (prod, stock_ini) in enumerate(STOCK_INICIAL.items()):
                actual = stock_ini + resumen_inv.get(prod, 0)
                [ck1, ck2, ck3][i].metric(prod, f"{actual:.1f} kg")

except Exception as e:
    st.error(f"Se detectó un error: {e}")
