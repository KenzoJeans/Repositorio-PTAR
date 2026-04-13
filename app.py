import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 1. Configuración de página y Estilo
st.set_page_config(page_title="SGA - PTAR - Kenzo Jeans", layout="wide", page_icon="💧")
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)

# --- ENCABEZADO PERSONALIZADO KENZO JEANS SAS ---
# Este bloque elimina el espacio extra que está cortando tu logo
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
        # Usamos use_container_width para que no se desborde ni se corte
        st.image("logo-white-kenzo.png", use_container_width=True)
    except Exception:
        st.markdown("**KENZO JEANS**")

with col_titulo:
    st.title("SGA - Gestión Integral PTAR - Kenzo Jeans SAS")

# --- CONFIGURACIÓN DE CONEXIÓN ---
# Asegúrate de reemplazar estas URLs con las tuyas
URL_DIRECTA_MANTO = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=746789412#gid=746789412"
URL_DIRECTA_TRATADA = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=1338797542#gid=1338797542"
URL_DIRECTA_QUIMICOS = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=170562532#gid=170562532"

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

    # Dataset 4: Kardex
    try:
        df_kardex = conn.read(spreadsheet=URL_DIRECTA_QUIMICOS, ttl=0)
    except:
        df_kardex = pd.DataFrame()

# --- CONFIGURACIÓN Y ESTILO DE BARRA LATERAL ---
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {
                min-width: 320px;
                max-width: 350px;
            }
        </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        try:
            st.image("logo-white-kenzo.png", use_container_width=True)
            st.markdown("---")
        except Exception:
            pass

        st.header("🔍 Filtros Dashboard")
        df_vert_filtrado = df_base_full.copy()

        # 1. Filtro de Procesos (Subimos este para dar prioridad)
        if not df_base_full.empty and 'proceso' in df_base_full.columns:
            procesos = sorted(df_base_full['proceso'].unique().tolist())
            sel = st.multiselect("Seleccionar Procesos:", procesos, default=procesos)
            df_vert_filtrado = df_vert_filtrado[df_vert_filtrado['proceso'].isin(sel)]

        # 2. Filtro de Químicos (Escritura)
        filtro_q = st.text_input("Filtrar por Químico:", "")
        if filtro_q and 'quimico' in df_vert_filtrado.columns:
            df_vert_filtrado = df_vert_filtrado[df_vert_filtrado['quimico'].astype(str).str.contains(filtro_q, case=False, na=False)]

        st.markdown("---")
        
        # 3. Filtro de Fechas (Al final para evitar que el pop-up se corte arriba)
        if not df_base_full.empty and 'fecha' in df_base_full.columns:
            st.subheader("📅 Rango de Tiempo")
            min_f, max_f = min(df_base_full['fecha']), max(df_base_full['fecha'])
            # Usamos una clave única para evitar conflictos
            rango = st.date_input("Seleccionar fechas:", [min_f, max_f], key="sidebar_date_range")
            
            if len(rango) == 2:
                df_vert_filtrado = df_vert_filtrado[(df_vert_filtrado['fecha'] >= rango[0]) & (df_vert_filtrado['fecha'] <= rango[1])]

    # --- DEFINICIÓN DE PESTAÑAS ---
    t1, t2, t3, t4 = st.tabs(["📊 Dashboard de vertimientos", "🧪 Agua tratada", "🛠️ Mantenimiento", "🧪 Consumo de químicos"])

    with t1:
        if not df_vert_filtrado.empty:
            # FILA 1: Métricas Principales
            m1, m2, m3, m4 = st.columns(4)
            avg_ph = df_vert_filtrado['ph'].mean()
            avg_temp = df_vert_filtrado['temp'].mean()
            avg_sst = df_vert_filtrado['sst'].mean()
            
            m1.metric("Promedio pH", f"{avg_ph:.2f}", delta="NORMA" if 6<=avg_ph<=9 else "ALERTA", delta_color="normal" if 6<=avg_ph<=9 else "inverse")
            m2.metric("Temp Promedio", f"{avg_temp:.1f} °C", delta="NORMAL" if avg_temp<=40 else "ALTA", delta_color="normal" if avg_temp<=40 else "inverse")
            m3.metric("SST Promedio", f"{avg_sst:.1f} mg/L")
            m4.metric("Registros", len(df_vert_filtrado))

            st.markdown("---")

            # FILA 2: Gráficas de pH
            col1, col2 = st.columns(2)
            with col1:
                st.write("**📈 Histórico de pH (Tintorería)**")
                st.plotly_chart(px.line(df_vert_filtrado.sort_values('fecha'), x='fecha', y='ph', markers=True, template="plotly_dark"), use_container_width=True)
            with col2:
                st.write("**📊 pH por proceso**")
                df_ph_p = df_vert_filtrado.groupby('proceso')['ph'].mean().reset_index()
                st.plotly_chart(px.bar(df_ph_p, x='proceso', y='ph', color='proceso', template="plotly_dark"), use_container_width=True)

           # FILA 3: Análisis de Temperatura con Degradado y Estilo
            col3, col4 = st.columns(2)
            with col3:
                st.markdown("<h4 style='text-align: center; color: #FFA726;'>🌡️ Tendencia de temperatura promedio</h4>", unsafe_allow_html=True)
                
                # 1. Crear la gráfica de área base con Plotly Express
                fig_temp_hist = px.area(
                    df_vert_filtrado.sort_values('fecha'), 
                    x='fecha', 
                    y='temp', 
                    template="plotly_dark",
                    # Usamos el color base naranja
                    color_discrete_sequence=['#FF9800'] 
                )

                # 2. Configurar el Degradado (Linear Gradient)
                # 'yanchor="bottom"' asegura que el degradado empiece desde la base (0 o min)
                fig_temp_hist.update_traces(
                    fillcolor="rgba(255, 152, 0, 0.4)", # Color de relleno con transparencia
                    line=dict(color="#FFB74D", width=2),   # Color y ancho de la línea del contorno
                    # Esta es la magia del degradado linear
                    fillpattern_shape="/",            # Patrón base para habilitar gradientes avanzados
                    fillpattern_fillmode="replace",
                    fillpattern_fgcolor="rgba(255, 87, 34, 0.8)", # Color secundario del gradiente (naranja más intenso)
                    selector=dict(type='scatter')
                )

                # 3. Pulir el layout (ejes y márgenes)
                fig_temp_hist.update_layout(
                    xaxis_title="Fecha", 
                    yaxis_title="Temperatura (°C)", 
                    margin=dict(l=20, r=20, t=20, b=20),
                    # Fondo transparente para que use el del dashboard
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                
                # Asegurar que el eje Y empiece en un valor lógico si hay datos
                if not df_vert_filtrado['temp'].isnull().all():
                    y_min = max(0, df_vert_filtrado['temp'].min() - 5)
                    y_max = df_vert_filtrado['temp'].max() + 5
                    fig_temp_hist.update_yaxes(range=[y_min, y_max])
                
                st.plotly_chart(fig_temp_hist, use_container_width=True)
                
            with col4:
                st.markdown("<h4 style='text-align: center; color: #FFD54F;'>📊 Temperatura por proceso</h4>", unsafe_allow_html=True)
                df_temp_proc = df_vert_filtrado.groupby('proceso')['temp'].mean().reset_index()
                
                # Usamos un amarillo/naranja vibrante para los puntos y líneas
                fig_temp_proc = px.line(
                    df_temp_proc, 
                    x='proceso', 
                    y='temp', 
                    markers=True, 
                    template="plotly_dark", 
                    color_discrete_sequence=['#FFD54F'] # Amarillo dorado
                )
                
                # Efecto de "Glow" o resplandor en los marcadores y línea
                fig_temp_proc.update_traces(
                    mode="markers+lines",
                    marker=dict(
                        size=10, 
                        line=dict(width=2, color='#FF8F00'), # Borde naranja
                        opacity=0.8
                    ),
                    line=dict(width=3)
                )

                fig_temp_proc.update_layout(
                    xaxis_title="Proceso", 
                    yaxis_title="Promedio Temp (°C)",
                    margin=dict(l=20, r=20, t=20, b=20),
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                
                st.plotly_chart(fig_temp_proc, use_container_width=True)

            # FILA 4: SST y Tabla
            st.write("**🍩 Promedio de Sólidos (SST) por proceso**")
            df_sst_p = df_vert_filtrado.groupby('proceso')['sst'].mean().reset_index()
            st.plotly_chart(px.pie(df_sst_p, values='sst', names='proceso', hole=0.5, template="plotly_dark"), use_container_width=True)
            
            st.write("**📄 Tabla de Datos**")
            st.dataframe(df_vert_filtrado, use_container_width=True)
        else:
            st.warning("Ajusta los filtros para ver datos.")

    # --- PESTAÑA 2: AGUA TRATADA ---
    with t2:
        st.subheader("🧪 Monitoreo de Agua Tratada - Kenzo Jeans")
        if df_tratada is not None and not df_tratada.empty:
            # Cálculos y Métricas
            avg_sst_sal = df_tratada['sst'].mean()
            sst_ent = df_base_full['sst'].mean() if not df_base_full.empty else 1
            rem = 100.0 if avg_sst_sal == 0 else max(0, (1 - (avg_sst_sal / sst_ent)) * 100)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("SST Salida", f"{avg_sst_sal:.1f} mg/L", delta=f"{rem:.1f}% Eficiencia")
            c2.metric("pH Salida", f"{df_tratada['ph'].mean():.2f}")
            c3.metric("Temp Salida", f"{df_tratada['temp'].mean():.1f} °C")
            c4.metric("Caudal Total", f"{df_tratada['caudal'].sum():.1f} m³")

            st.markdown("---")
            # Gráficas de Agua Tratada
            col_a, col_b = st.columns(2)
            with col_a:
                st.write("**📈 pH y 🌡️ Temperatura**")
                st.plotly_chart(px.line(df_tratada.sort_values('fecha'), x='fecha', y=['ph', 'temp'], template="plotly_dark"), use_container_width=True)
            with col_b:
                st.write("**💧 Eficiencia de Remoción (Área)**")
                import plotly.graph_objects as go
                fig_ef = go.Figure()
                fig_ef.add_trace(go.Scatter(x=df_tratada['fecha'], y=[sst_ent]*len(df_tratada), fill='tozeroy', name='Entrada', line_color='gray'))
                fig_ef.add_trace(go.Scatter(x=df_tratada['fecha'], y=df_tratada['sst'], fill='tozeroy', name='Salida', line_color='#00E676'))
                fig_ef.update_layout(template="plotly_dark", margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig_ef, use_container_width=True)
            
            st.write("**📄 Registros Recientes**")
            st.dataframe(df_tratada.sort_values('fecha', ascending=False), use_container_width=True)
        else:
            st.info("No hay datos en Agua Tratada.")

    # --- PESTAÑA 3: MANTENIMIENTO ---
    with t3:
        st.subheader("🛠️ Gestión de Mantenimiento - Kenzo Jeans")
        if df_manto is not None and not df_manto.empty:
            # Normalización de columnas para evitar el error 'FECHA'
            df_manto.columns = df_manto.columns.str.strip().str.upper()
            if 'SALUD' in df_manto.columns:
                df_manto['SALUD'] = pd.to_numeric(df_manto['SALUD'], errors='coerce').fillna(0)
            
            col_f = 'FECHA' if 'FECHA' in df_manto.columns else df_manto.columns[0]
            
            # Tarjetas de Equipos
            if 'EQUIPO' in df_manto.columns:
                list_eq = df_manto['EQUIPO'].unique()
                c_cards = st.columns(3)
                for idx, nombre_eq in enumerate(list_eq):
                    status_eq = df_manto[df_manto['EQUIPO'] == nombre_eq].iloc[-1]
                    s_val = status_eq['SALUD']
                    b_color = "#4CAF50" if s_val >= 8 else "#FFEB3B" if s_val >= 6 else "#F44336"
                    with c_cards[idx % 3]:
                        st.markdown(f'<div style="background:#1E1E1E; padding:15px; border-radius:10px; border-left:8px solid {b_color}; margin-bottom:10px;"><b>{nombre_eq}</b><br><span style="font-size:20px;">❤️ {s_val}/10</span></div>', unsafe_allow_html=True)

            st.markdown("---")
            st.write("**📊 Tendencia de Salud**")
            st.plotly_chart(px.line(df_manto.sort_values(col_f), x=col_f, y='SALUD', color='EQUIPO', markers=True, template="plotly_dark"), use_container_width=True)
        else:
            st.info("No hay datos en Mantenimiento.")

    with t4:
        st.subheader("📦 Inventario y Consumo - Kenzo Jeans")
        STOCK_INICIAL = {"SULFATO DE ALUMINIO": 119, "CAL": 79, "POLIMERO": 50}
        if not df_kardex.empty:
            df_kardex.columns = df_kardex.columns.str.strip()
            df_kardex['CANTIDAD'] = pd.to_numeric(df_kardex['CANTIDAD'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
            df_kardex['fecha_dt'] = pd.to_datetime(df_kardex['FECHA'], errors='coerce').dt.date
            df_limpio = df_kardex.dropna(subset=['fecha_dt'])

            if not df_limpio.empty:
                st.write("### 📅 Consumo en Periodo")
                f_min, f_max = df_limpio['fecha_dt'].min(), df_limpio['fecha_dt'].max()
                f_rango = st.date_input("Rango:", [f_min, f_max], key="k_date")
                
                if len(f_rango) == 2:
                    df_sal = df_limpio[(df_limpio['QUE PROCESO VA A REALIZAR'] == 'SALIDA') & (df_limpio['fecha_dt'] >= f_rango[0]) & (df_limpio['fecha_dt'] <= f_rango[1])]
                    sum_sal = df_sal.groupby('NOMBRE DEL QUIMICO')['CANTIDAD'].sum().to_dict()
                    c_c = st.columns(3)
                    for i, p in enumerate(STOCK_INICIAL.keys()):
                        with c_c[i]: st.metric(f"Salida {p}", f"{sum_sal.get(p, 0)} kg")

            st.markdown("---")
            st.write("### 🔋 Existencias Actuales")
            df_limpio['neto'] = df_limpio.apply(lambda x: x['CANTIDAD'] if x['QUE PROCESO VA A REALIZAR'] == 'ENTRADA' else -x['CANTIDAD'], axis=1)
            movs = df_limpio.groupby('NOMBRE DEL QUIMICO')['neto'].sum().to_dict()
            cols_s = st.columns(3)
            for i, (prod, ini) in enumerate(STOCK_INICIAL.items()):
                act = ini + movs.get(prod, 0)
                with cols_s[i]:
                    st.metric(prod, f"{act} kg", delta="REABASTECER" if act < 20 else "OK", delta_color="inverse" if act < 20 else "normal")

except Exception as e:
    st.error(f"Se detectó un error: {e}")
