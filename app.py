import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 1. Configuración de página
st.set_page_config(page_title="Sistema Control PTAR", layout="wide", page_icon="💧")
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)
st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# --- CONFIGURACIÓN DE CONEXIONES (REEMPLAZAR CON TUS URLS) ---
URL_MANTO = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=746789412#gid=746789412" 
URL_TRATADA = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=1338797542#gid=1338797542" 

# 2. Función de limpieza REFORZADA (Evita el error 'sst')
def limpiar_datos_ptar(df):
    if df is None or df.empty: return pd.DataFrame()
    df.columns = df.columns.str.strip()
    
    # Mapeo exhaustivo para detectar columnas sin importar cómo se escriban
    mapeo = {
        'ph': 'ph', 'pH': 'ph', 'PH': 'ph',
        'temp': 'temp', 'Temperatura': 'temp', 'TEMP': 'temp',
        'sst': 'sst', 'SST': 'sst', 'Solidos': 'sst', 'Solidos suspendidos': 'sst',
        'Fecha del reporte': 'fecha', 'fecha': 'fecha', 'Marca temporal': 'fecha_h',
        'Proceso a reportar': 'proceso'
    }
    df = df.rename(columns={k: v for k, v in mapeo.items() if k in df.columns})
    
    # Procesamiento de columnas críticas (Manejo de ceros y vacíos)
    for col in ['ph', 'temp', 'sst']:
        if col in df.columns:
            # Convierte a número, reemplaza comas por puntos y llena vacíos con 0
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        else:
            # Si la columna no existe, la crea con 0 para evitar que la app se rompa
            df[col] = 0.0 
            
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce').dt.date
    return df

# 3. Carga de Datos Principal
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Datos de Vertimiento (Hoja Base desde Secrets)
    df_vert_raw = conn.read(ttl=0)
    df_vert = limpiar_datos_ptar(df_vert_raw)

    # Datos de Agua Tratada (URL Directa)
    try:
        df_trat_raw = conn.read(spreadsheet=URL_TRATADA, ttl=0)
        df_tratada = limpiar_datos_ptar(df_trat_raw)
    except:
        df_tratada = pd.DataFrame()

    # Datos de Mantenimiento (URL Directa)
    try:
        df_manto = conn.read(spreadsheet=URL_MANTO, ttl=0)
        df_manto.columns = df_manto.columns.str.strip()
    except:
        df_manto = pd.DataFrame()

    # --- BARRA LATERAL (FILTROS DEL CÓDIGO BASE) ---
    st.sidebar.header("Filtros de Análisis")
    if not df_vert.empty and 'fecha' in df_vert.columns:
        min_f, max_f = min(df_vert['fecha']), max(df_vert['fecha'])
        rango = st.sidebar.date_input("Rango de fechas (Vertimientos):", [min_f, max_f])
        if len(rango) == 2:
            df_vert = df_vert[(df_vert['fecha'] >= rango[0]) & (df_vert['fecha'] <= rango[1])]

    # --- TABS PRINCIPALES ---
    t1, t2, t3 = st.tabs(["📊 Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with t1:
        st.subheader("Análisis de Entrada (Agua Cruda)")
        if not df_vert.empty:
            m1, m2, m3 = st.columns(3)
            m1.metric("pH Promedio", f"{df_vert['ph'].mean():.2f}")
            m2.metric("SST Promedio", f"{df_vert['sst'].mean():.2f} mg/L")
            m3.metric("Total Reportes", len(df_vert))
            
            fig_v = px.line(df_vert.sort_values('fecha'), x='fecha', y='ph', title="Histórico pH Entrada", markers=True)
            st.plotly_chart(fig_v, use_container_width=True)
            st.dataframe(df_vert, use_container_width=True)

    with t2:
        st.subheader("🧪 Eficiencia de Remoción")
        if not df_tratada.empty:
            # Lógica de Eficiencia (Protección contra división por cero)
            sst_ent = df_vert['sst'].mean() if not df_vert.empty else 0
            sst_sal = df_tratada['sst'].mean()
            remocion = ((sst_ent - sst_sal) / sst_ent) * 100 if sst_ent > 0 else 0

            c1, c2, c3 = st.columns(3)
            c1.metric("SST Salida", f"{sst_sal:.1f} mg/L", delta=f"{remocion:.1f}% Remoción")
            c2.metric("pH Salida", f"{df_tratada['ph'].mean():.2f}")
            c3.metric("Estado", "ÓPTIMO" if sst_sal <= 50 else "FUERA DE NORMA")

            st.markdown("---")
            st.write("**Historial de Salida:**")
            st.dataframe(df_tratada, use_container_width=True)
        else:
            st.info("No hay datos registrados en la pestaña de Agua Tratada.")

    with t3:
        st.subheader("🛠️ Panel de Mantenimiento por Equipo")
        if not df_manto.empty:
            # Asegurar que Salud sea numérico para las tarjetas
            if 'SALUD' in df_manto.columns:
                df_manto['SALUD'] = pd.to_numeric(df_manto['SALUD'], errors='coerce').fillna(0)

            equipos = df_manto['EQUIPO'].unique()
            cols_cards = st.columns(3)
            
            for i, eq_nombre in enumerate(equipos):
                datos_eq = df_manto[df_manto['EQUIPO'] == eq_nombre].iloc[-1]
                salud_val = datos_eq['SALUD']
                color = "#4CAF50" if salud_val >= 8 else "#FFEB3B" if salud_val >= 6 else "#F44336"
                
                with cols_cards[i % 3]:
                    st.markdown(f"""
                        <div style="background-color: #1E1E1E; padding: 15px; border-radius: 10px; border-top: 5px solid {color}; margin-bottom: 15px;">
                            <h4 style="margin:0;">⚙️ {eq_nombre}</h4>
                            <p style="color:{color}; font-size:18px; font-weight:bold; margin:0;">{salud_val}/10</p>
                            <p style="font-size:11px; color:#888;">Estado: {datos_eq.get('ESTADO', 'N/A')}</p>
                            <hr style="margin:8px 0; border:0.1px solid #333;">
                            <p style="font-size:11px; height:35px; overflow:hidden;">{datos_eq.get('QUE SE REALIZO', '')[:75]}...</p>
                        </div>
                    """, unsafe_allow_html=True)
            
            with st.expander("Ver tabla completa de mantenimiento"):
                st.dataframe(df_manto, use_container_width=True)

except Exception as e:
    st.error(f"Error general en la aplicación: {e}")
