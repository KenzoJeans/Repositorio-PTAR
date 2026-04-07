import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 1. Configuración de página y Estilo
st.set_page_config(page_title="Sistema Control PTAR", layout="wide", page_icon="💧")
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)
st.markdown('<p style="font-size:30px; font-weight:bold; color:#1E88E5;">🏗️ Gestión Integral - Planta de Tratamiento</p>', unsafe_allow_html=True)

# --- CONFIGURACIÓN DE CONEXIÓN ---
# Reemplaza con tus URLs reales que contienen el gid=...
URL_DIRECTA_MANTO = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=746789412#gid=746789412" 
URL_DIRECTA_TRATADA = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=1338797542#gid=1338797542"

# 2. Función de limpieza de datos REFORZADA
def limpiar_datos_ptar(df):
    if df is None or df.empty:
        return pd.DataFrame()
    
    # Limpieza de nombres de columnas y blindaje contra duplicados físicos
    df.columns = df.columns.str.strip()
    df = df.loc[:, ~df.columns.duplicated()]
    
    # Mapeo flexible para unificar ambos formularios (Entrada y Salida)
    mapeo = {
        'ph': 'ph', 'pH': 'ph', 'PH': 'ph', 'pH Tratada': 'ph',
        'temp': 'temp', 'Temperatura': 'temp', 'Temperatura Tratada': 'temp',
        'sst': 'sst', 'SST': 'sst', 'SST Tratada': 'sst', 'Solidos suspendidos': 'sst',
        'Conductividad Tratada': 'cond', 'Caudal tratado': 'caudal',
        'Fecha': 'fecha', 'fecha': 'fecha', 'Fecha del reporte': 'fecha', 
        'Marca temporal': 'fecha_h',
        'Proceso a reportar': 'proceso',
        'Productos quimicos utilizados en el proceso': 'quimicos'
    }
    
    # Renombrado seguro para evitar el error "cannot assemble with duplicate keys"
    nuevos_nombres = {}
    for col in df.columns:
        if col in mapeo:
            target = mapeo[col]
            if target not in nuevos_nombres.values():
                nuevos_nombres[col] = target
    
    df = df.rename(columns=nuevos_nombres)

    # Asegurar que las columnas críticas sean numéricas y existan
    columnas_num = ['ph', 'temp', 'sst', 'cond', 'caudal']
    for col in columnas_num:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        else:
            df[col] = 0.0
    
    # Lógica de fecha inteligente
    if 'fecha' not in df.columns and 'fecha_h' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha_h'], errors='coerce').dt.date
    elif 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce').dt.date
    
    # En la base de vertimientos, mantenemos el filtro de pH para limpiar filas vacías
    if 'ph' in df.columns and len(df) > 0:
        return df[df['ph'] > 0]
    return df

# 3. Conexión y Carga de Datos
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Carga Vertimiento (Hoja principal de Secrets)
    df_raw = conn.read(ttl=0) 
    df_base = limpiar_datos_ptar(df_raw)

    # Carga Agua Tratada
    try:
        df_tratada = limpiar_datos_ptar(conn.read(spreadsheet=URL_DIRECTA_TRATADA, ttl=0))
    except:
        df_tratada = pd.DataFrame()

    # Carga Mantenimiento
    try:
        df_manto = conn.read(spreadsheet=URL_DIRECTA_MANTO, ttl=0)
        df_manto.columns = df_manto.columns.str.strip()
    except:
        df_manto = pd.DataFrame()

    # --- BARRA LATERAL (FILTROS) ---
    try:
        st.sidebar.image("logo-white-kenzo.png", use_container_width=True)
    except:
        pass

    st.sidebar.header("Filtros de Análisis")
    
    if not df_base.empty and 'fecha' in df_base.columns:
        min_f, max_f = min(df_base['fecha']), max(df_base['fecha'])
        rango_fechas = st.sidebar.date_input("Rango de fechas:", [min_f, max_f])
        if len(rango_fechas) == 2:
            df_base = df_base[(df_base['fecha'] >= rango_fechas[0]) & (df_base['fecha'] <= rango_fechas[1])]

    if not df_base.empty and 'proceso' in df_base.columns:
        lista_p = sorted(df_base['proceso'].unique().tolist())
        procesos_sel = st.sidebar.multiselect("Selecciona el Proceso:", lista_p, default=lista_p)
        df_filtrado = df_base[df_base['proceso'].isin(procesos_sel)]
    else:
        df_filtrado = df_base

    # --- CUERPO PRINCIPAL (TABS) ---
    t1, t2, t3 = st.tabs(["📊 Dashboard Vertimientos", "🧪 Agua Tratada", "🛠️ Mantenimiento"])

    with t1:
        if not df_filtrado.empty:
            m1, m2, m3, m4 = st.columns(4)
            avg_ph = df_filtrado['ph'].mean()
            avg_temp = df_filtrado['temp'].mean()
            avg_sst = df_filtrado['sst'].mean()

            m1.metric("Promedio pH", f"{avg_ph:.2f}", 
                      delta="EN NORMA" if 6.0 <= avg_ph <= 9.0 else "FUERA DE RANGO",
                      delta_color="normal" if 6.0 <= avg_ph <= 9.0 else "inverse")
            m2.metric("Temp Promedio", f"{avg_temp:.1f} °C",
                      delta="ESTABLE" if avg_temp <= 40 else "ELEVADA")
            m3.metric("SST Promedio", f"{avg_sst:.2f}",
                      delta="ÓPTIMO" if avg_sst <= 50 else "CRÍTICO")
            m4.metric("Total Registros", len(df_filtrado))

            st.subheader("📈 Análisis de pH")
            fig_t = px.line(df_filtrado.sort_values('fecha'), x='fecha', y='ph', markers=True, template="plotly_dark")
            fig_t.add_hline(y=9.0, line_dash="dash", line_color="red")
            fig_t.add_hline(y=6.0, line_dash="dash", line_color="red")
            st.plotly_chart(fig_t, use_container_width=True)
            
            st.dataframe(df_filtrado, use_container_width=True)
        else:
            st.warning("No hay datos para mostrar en Vertimientos.")

    with t2:
        st.subheader("🧪 Monitoreo de Agua Tratada (Salida)")
        if not df_tratada.empty:
            avg_sst_sal = df_tratada['sst'].mean()
            avg_ph_sal = df_tratada['ph'].mean()
            avg_temp_sal = df_tratada['temp'].mean()

            # Lógica de Remoción SST
            if avg_sst_sal == 0:
                texto_rem = "100% Remoción"
                color_rem = "normal"
            else:
                sst_ent = df_filtrado['sst'].mean() if not df_filtrado.empty else 0
                rem = ((sst_ent - avg_sst_sal) / sst_ent) * 100 if sst_ent > 0 else 0
                texto_rem = f"{rem:.1f}% Remoción"
                color_rem = "normal" if rem > 80 else "inverse"

            # Métricas con indicadores solicitados
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("SST Salida", f"{avg_sst_sal:.1f} mg/L", delta=texto_rem, delta_color=color_rem)
            c2.metric("pH Promedio", f"{avg_ph_sal:.2f}", 
                      delta="DENTRO DE NORMA" if 6.0 <= avg_ph_sal <= 9.0 else "FUERA DE RANGO",
                      delta_color="normal" if 6.0 <= avg_ph_sal <= 9.0 else "inverse")
            c3.metric("Temp. Promedio", f"{avg_temp_sal:.1f} °C", 
                      delta="NORMAL" if avg_temp_sal <= 40 else "ALTA",
                      delta_color="normal" if avg_temp_sal <= 40 else "inverse")
            c4.metric("Caudal Total", f"{df_tratada['caudal'].sum():.1f} m³")

            st.markdown("---")
            cola, colb = st.columns(2)
            with cola:
                st.plotly_chart(px.line(df_tratada.sort_values('fecha'), x='fecha', y=['ph', 'temp'], 
                                       markers=True, title="Tendencia pH vs Temperatura", template="plotly_dark"), use_container_width=True)
            with colb:
                st.plotly_chart(px.area(df_tratada.sort_values('fecha'), x='fecha', y='cond', 
                                   title="Conductividad (µS/cm)", template="plotly_dark", color_discrete_sequence=['#00CC96']), use_container_width=True)

            st.markdown("---")
            st.plotly_chart(px.bar(df_tratada.sort_values('fecha'), x='fecha', y='caudal', 
                                title="Volumen Tratado por Día (m³)", template="plotly_dark", color='caudal', color_continuous_scale='Blues'), use_container_width=True)
        else:
            st.info("Módulo de Agua Tratada sin datos recientes.")

    with t3:
        st.subheader("🛠️ Panel de Mantenimiento por Equipo")
        if not df_manto.empty:
            if 'SALUD' in df_manto.columns:
                df_manto['SALUD'] = pd.to_numeric(df_manto['SALUD'], errors='coerce').fillna(0)

            avg_s_global = df_manto['SALUD'].mean() if 'SALUD' in df_manto.columns else 0
            
            st.markdown(f"""
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 20px;">
                    <div style="background-color: #1E1E1E; padding: 15px; border-radius: 10px; border-left: 5px solid #4CAF50;">
                        <small style="color: #888;">Salud Global</small><br><strong style="font-size: 20px;">{avg_s_global:.1f}/10</strong>
                    </div>
                    <div style="background-color: #1E1E1E; padding: 15px; border-radius: 10px; border-left: 5px solid #2196F3;">
                        <small style="color: #888;">Equipos Activos</small><br><strong style="font-size: 20px;">{len(df_manto['EQUIPO'].unique()) if 'EQUIPO' in df_manto.columns else 0}</strong>
                    </div>
                    <div style="background-color: #1E1E1E; padding: 15px; border-radius: 10px; border-left: 5px solid #9C27B0;">
                        <small style="color: #888;">Reportes Totales</small><br><strong style="font-size: 20px;">{len(df_manto)}</strong>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            if 'EQUIPO' in df_manto.columns:
                equipos = df_manto['EQUIPO'].unique()
                cols_eq = st.columns(3)
                for i, eq_nombre in enumerate(equipos):
                    datos = df_manto[df_manto['EQUIPO'] == eq_nombre].iloc[-1]
                    salud_val = datos['SALUD']
                    color_card = "#4CAF50" if salud_val >= 8 else "#FFEB3B" if salud_val >= 6 else "#F44336"
                    f_reporte = datos.get('Fecha', datos.get('Marca temporal', 'N/A'))
                    tarea = datos.get('QUE SE REALIZO', 'Sin descripción')
                    proximo = datos.get('FECHA PROX MANTENIMIENTO', 'N/A')

                    with cols_eq[i % 3]:
                        st.markdown(f"""
                            <div style="background-color: #1E1E1E; padding: 15px; border-radius: 10px; border-top: 5px solid {color_card}; margin-bottom: 15px;">
                                <h4 style="margin-bottom: 5px;">⚙️ {eq_nombre}</h4>
                                <p style="font-size: 14px; margin: 0; color: {color_card};">Salud Actual: <b>{salud_val}/10</b></p>
                                <p style="font-size: 11px; color: #888; margin-top: 5px;">Último registro: {f_reporte}</p>
                                <hr style="margin: 10px 0; border: 0.5px solid #333;">
                                <p style="font-size: 11px; height: 40px; overflow: hidden;">{str(tarea)[:85]}...</p>
                                <p style="font-size: 10px; color: #555; text-align: right; margin-top: 5px;">Próximo Manto: {proximo}</p>
                            </div>
                        """, unsafe_allow_html=True)
            
            with st.expander("Ver Historial Completo"):
                st.dataframe(df_manto, use_container_width=True)
        else:
            st.warning("No se encontraron registros de mantenimiento.")

except Exception as e:
    st.error(f"Error general en la aplicación: {e}")
