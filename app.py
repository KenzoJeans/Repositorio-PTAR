import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import date, datetime  # <--- ESTA ES LA LÍNEA QUE FALTA

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
        
        # 3. Filtro de Fechas
        rango = None  # ← al mismo nivel que el if
        if not df_base_full.empty and 'fecha' in df_base_full.columns:
            st.subheader("📅 Rango de Tiempo")  # ← 4 espacios más adentro
            
            limite_inferior = date(2024, 1, 1) 
            limite_superior = date.today()
            
            def_start = df_base_full['fecha'].min()
            def_end = df_base_full['fecha'].max()
            
            rango = st.date_input(
                "Seleccionar fechas:", 
                [def_start, def_end], 
                min_value=limite_inferior, 
                max_value=limite_superior,
                key="sidebar_date_range"
            )
            
            if isinstance(rango, (list, tuple)) and len(rango) == 2:
                inicio, fin = rango
                df_vert_filtrado = df_vert_filtrado[
                    (df_vert_filtrado['fecha'] >= inicio) & (df_vert_filtrado['fecha'] <= fin)
                ]
                if not df_tratada.empty and 'fecha' in df_tratada.columns:
                    df_tratada = df_tratada[(df_tratada['fecha'] >= inicio) & (df_tratada['fecha'] <= fin)]

                if not df_manto.empty:
                    col_fecha_m_sidebar = 'FECHA' if 'FECHA' in df_manto.columns else df_manto.columns[0]
                    df_manto[col_fecha_m_sidebar] = pd.to_datetime(
                        df_manto[col_fecha_m_sidebar], dayfirst=True, errors='coerce'
                    ).dt.date
                    df_manto = df_manto[
                        (df_manto[col_fecha_m_sidebar] >= inicio) & 
                        (df_manto[col_fecha_m_sidebar] <= fin)
                    ]

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
                fig_temp_proc = px.bar(
                    df_temp_proc, 
                    x='proceso', 
                    y='temp',
                    color='proceso',
                    template="plotly_dark",
                    color_discrete_sequence=['#FFD54F', '#FFA726', '#FF7043', '#66BB6A']
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

    with t2:
        st.subheader("🧪 Monitoreo de Agua Tratada")
        
        if not df_tratada.empty:
            # --- CÁLCULOS DE EFICIENCIA ---
            avg_sst_sal = df_tratada['sst'].mean()
            # Obtenemos el SST de entrada promedio del dashboard principal para comparar
            sst_ent = df_base_full['sst'].mean() if not df_base_full.empty else 1
            
            # Lógica: SST=0 significa 100% de remoción
            if avg_sst_sal == 0:
                remocion = 100.0
            else:
                remocion = max(0, (1 - (avg_sst_sal / sst_ent)) * 100)

            # --- TARJETAS (KPIs) ---
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("SST Salida (Prom)", f"{avg_sst_sal:.1f} mg/L", delta=f"{remocion:.1f}% Eficiencia")
            c2.metric("pH Salida", f"{df_tratada['ph'].mean():.2f}", delta="OK" if 6<=df_tratada['ph'].mean()<=9 else "FUERA")
            c3.metric("Temp Salida", f"{df_tratada['temp'].mean():.1f} °C", delta="ESTABLE" if df_tratada['temp'].mean()<=40 else "ALTA")
            c4.metric("Caudal Total", f"{df_tratada['caudal'].sum():.1f} m³")

            st.markdown("---")

            # --- FILA 1: COMPORTAMIENTO FÍSICO-QUÍMICO ---
            col_a, col_b = st.columns(2)
            with col_a:
                st.write("**📈 pH del Agua Tratada (Tiempo)**")
                fig_ph_t = px.line(df_tratada.sort_values('fecha'), x='fecha', y='ph', 
                                   markers=True, template="plotly_dark", color_discrete_sequence=['#00C853'])
                # Líneas de referencia para cumplimiento legal
                fig_ph_t.add_hline(y=6, line_dash="dash", line_color="red", annotation_text="Límite Inf")
                fig_ph_t.add_hline(y=9, line_dash="dash", line_color="red", annotation_text="Límite Sup")
                st.plotly_chart(fig_ph_t, use_container_width=True)

            with col_b:
                st.write("**🌡️ Temperatura de Salida (Tiempo)**")
                # Usamos el naranja que ya definimos para mantener consistencia
                fig_temp_t = px.area(df_tratada.sort_values('fecha'), x='fecha', y='temp', 
                                     template="plotly_dark", color_discrete_sequence=['#FFA726'])
                fig_temp_t.add_hline(y=40, line_dash="dash", line_color="red", annotation_text="Máx Permisible")
                st.plotly_chart(fig_temp_t, use_container_width=True)

            # --- FILA 2: EFICIENCIA Y VOLUMEN ---
            col_c, col_d = st.columns(2)
            with col_c:
                st.write("**💧 Remoción de Sólidos (Entrada vs Salida)**")
                # Creamos un comparativo rápido
                df_comp = pd.DataFrame({
                    'Etapa': ['Entrada (Crudo)', 'Salida (Tratada)'],
                    'SST (mg/L)': [sst_ent, avg_sst_sal]
                })
                fig_rem = px.bar(df_comp, x='Etapa', y='SST (mg/L)', color='Etapa',
                                 color_discrete_map={'Entrada (Crudo)': '#78909C', 'Salida (Tratada)': '#00E676'},
                                 template="plotly_dark")
                st.plotly_chart(fig_rem, use_container_width=True)

            with col_d:
                st.write("**📊 Volumen de Agua Tratada por Día**")
                fig_cau = px.bar(df_tratada.sort_values('fecha'), x='fecha', y='caudal',
                                 template="plotly_dark", color_discrete_sequence=['#29B6F6'])
                st.plotly_chart(fig_cau, use_container_width=True)

        else:
            st.warning("No hay datos registrados en la hoja de 'Agua Tratada'.")

    with t3:
        st.subheader("🛠️ Estado de Equipos - Kenzo Jeans")
        
        if not df_manto.empty:
    # ← PRIMERO normalizar columnas a mayúsculas
    df_manto.columns = df_manto.columns.str.strip().str.upper()
    col_fecha_m_sidebar = 'FECHA' if 'FECHA' in df_manto.columns else df_manto.columns[0]
    df_manto[col_fecha_m_sidebar] = pd.to_datetime(
        df_manto[col_fecha_m_sidebar], dayfirst=True, errors='coerce'
    ).dt.date
    df_manto = df_manto[
        (df_manto[col_fecha_m_sidebar] >= inicio) & 
        (df_manto[col_fecha_m_sidebar] <= fin)
    ]

        if 'SALUD' in df_manto.columns:
            df_manto['SALUD'] = pd.to_numeric(df_manto['SALUD'], errors='coerce').fillna(0)

        col_fecha_m = 'FECHA' if 'FECHA' in df_manto.columns else df_manto.columns[0]

        # ← AÑADIR: parseo de fecha si aún está como texto
        if df_manto[col_fecha_m].dtype == object:
            df_manto[col_fecha_m] = pd.to_datetime(
                df_manto[col_fecha_m], dayfirst=True, errors='coerce'
                ).dt.date
            
            # --- 2. TARJETAS DE SALUD INDIVIDUAL ---
            if 'EQUIPO' in df_manto.columns:
                equipos = df_manto['EQUIPO'].unique()
                cols_eq = st.columns(3)
                
                for i, eq in enumerate(equipos):
                    # Obtenemos el registro más reciente para este equipo
                    ult_reg = df_manto[df_manto['EQUIPO'] == eq].iloc[-1]
                    val_s = ult_reg['SALUD']
                    fecha_val = ult_reg[col_fecha_m]
                    
                    # Lógica de colores (Semáforo)
                    color = "#4CAF50" if val_s >= 8 else "#FFEB3B" if val_s >= 6 else "#F44336"
                    desc_estado = "ÓPTIMO" if val_s >= 8 else "PREVENTIVO" if val_s >= 6 else "CRÍTICO"
                    
                    with cols_eq[i % 3]:
                        st.markdown(f"""
                            <div style="background:#1E1E1E; padding:20px; border-radius:15px; border-left:10px solid {color}; margin-bottom:20px; border-top: 1px solid #333;">
                                <h4 style="margin:0; color:white;">{eq}</h4>
                                <p style="color:{color}; font-weight:bold; margin:5px 0; font-size:13px;">{desc_estado}</p>
                                <h2 style="margin:10px 0;"> 📈 {val_s}/10</h2>
                                <small style="color:#888;">Última revisión: {fecha_val}</small>
                            </div>
                        """, unsafe_allow_html=True)
            
            # --- 3. ANÁLISIS VISUAL AVANZADO (REEMPLAZO DE LA GRÁFICA) ---
            st.markdown("---")
            col_v1, col_v2 = st.columns([2, 1])

            with col_v1:
                st.write("**🌡️ Mapa de Salud Semanal (Heatmap)**")
                # Creamos una matriz de Salud: Equipos vs Fecha
                # Esto permite ver bloques de color: Verde (sano), Rojo (problema)
                df_pivot = df_manto.pivot_table(
                    index='EQUIPO', 
                    columns=col_fecha_m, 
                    values='SALUD', 
                    aggfunc='last'
                ).fillna(0)

                fig_heat = px.imshow(
                    df_pivot,
                    labels=dict(x="Fecha", y="Equipo", color="Salud"),
                    x=df_pivot.columns,
                    y=df_pivot.index,
                    color_continuous_scale=['#F44336', '#FFEB3B', '#4CAF50'], # Rojo -> Amarillo -> Verde
                    aspect="auto",
                    template="plotly_dark"
                )
                fig_heat.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=350)
                st.plotly_chart(fig_heat, use_container_width=True)

            with col_v2:
                st.write("**📢 Alertas de Mantenimiento**")
                # Filtramos equipos con salud menor a 7 para mostrar como tareas pendientes
                pendientes = df_manto[df_manto['SALUD'] < 7].sort_values(col_fecha_m, ascending=False).drop_duplicates('EQUIPO')
                
                if not pendientes.empty:
                    for _, row in pendientes.iterrows():
                        st.warning(f"**{row['EQUIPO']}**: Salud en {row['SALUD']}/10. Requiere revisión técnica inmediata.")
                else:
                    st.success("✅ Todos los equipos operan en rangos seguros.")

            # --- 4. TABLA DE BITÁCORA ---
            with st.expander("📝 Ver historial completo de intervenciones"):
                st.dataframe(df_manto.sort_values(col_fecha_m, ascending=False), use_container_width=True)
    with t4:
        st.subheader("📦 Gestión de Inventarios y Consumo - Kenzo Jeans")
        
        STOCK_INICIAL = {"SULFATO DE ALUMINIO": 119, "CAL": 79, "POLIMERO": 24.118}
        
        if not df_kardex.empty:
            df_kardex.columns = df_kardex.columns.str.strip().str.upper()
            df_kardex['CANTIDAD'] = pd.to_numeric(df_kardex['CANTIDAD'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
            
            # --- FILA 1: KPIs ---
            df_kardex['NETO'] = df_kardex.apply(lambda x: x['CANTIDAD'] if x['QUE PROCESO VA A REALIZAR'] == 'ENTRADA' else -x['CANTIDAD'], axis=1)
            resumen_inv = df_kardex.groupby('NOMBRE DEL QUIMICO')['NETO'].sum().to_dict()
            
            ck1, ck2, ck3 = st.columns(3)
            for i, (prod, stock_ini) in enumerate(STOCK_INICIAL.items()):
                actual = stock_ini + resumen_inv.get(prod, 0)
                col_k = [ck1, ck2, ck3][i]
                alerta = "⚠️ REABASTECER" if actual < 20 else "✅ STOCK OK"
                col_k.metric(prod, f"{actual:.1f} kg", delta=alerta, delta_color="inverse" if actual < 20 else "normal")
                
                # --- SECCIÓN: CONSUMO EN EL PERIODO (VERSIÓN ULTRA-ROBUSTA) ---
            st.markdown("### 📊 Consumo en el Periodo Seleccionado")
            
            df_k_periodo = df_kardex.copy()
            
            # 1. LIMPIEZA DE NÚMEROS: Forzamos conversión a decimal (float)
            df_k_periodo['CANTIDAD'] = (
                df_k_periodo['CANTIDAD']
                .astype(str)
                .str.replace(',', '.')
                .str.replace(r'[^0-9.]', '', regex=True) # Elimina cualquier caracter no numérico
            )
            df_k_periodo['CANTIDAD'] = pd.to_numeric(df_k_periodo['CANTIDAD'], errors='coerce').fillna(0)

            # 2. LIMPIEZA DE FECHAS: Aseguramos que Pandas las entienda bien
            df_k_periodo['FECHA'] = pd.to_datetime(df_k_periodo['FECHA'], dayfirst=True, errors='coerce').dt.date

            if isinstance(rango, (list, tuple)) and len(rango) == 2:
                inicio, fin = rango
                # Filtramos el periodo
                df_k_periodo = df_k_periodo[(df_k_periodo['FECHA'] >= inicio) & (df_k_periodo['FECHA'] <= fin)]
                
                # 3. Filtrar SALIDAS y Sumar
                # Usamos .str.upper() por si acaso en la hoja escribieron 'salida' en minúsculas
                df_salidas_periodo = df_k_periodo[df_k_periodo['QUE PROCESO VA A REALIZAR'].astype(str).str.upper() == 'SALIDA']
                consumo_periodo = df_salidas_periodo.groupby('NOMBRE DEL QUIMICO')['CANTIDAD'].sum().to_dict()
                
                # Renderizado de tarjetas
                cs1, cs2, cs3 = st.columns(3)
                quimicos_objetivo = ["SULFATO DE ALUMINIO", "CAL", "POLIMERO"]
                columnas_salida = [cs1, cs2, cs3]

                for i, quimico in enumerate(quimicos_objetivo):
                    total_salida = consumo_periodo.get(quimico, 0.0)
                    # Contamos cuántos registros sumaron para este químico
                    n_registros = len(df_salidas_periodo[df_salidas_periodo['NOMBRE DEL QUIMICO'] == quimico])
                    
                    columnas_salida[i].metric(
                        label=f"Salidas: {quimico}",
                        value=f"{total_salida:.2f} kg",
                        delta=f"{n_registros} registros",
                        delta_color="normal"
                    )
            
            st.markdown("---")

            # --- FILA 2: DONA Y RESUMEN ---
            col_dona, col_info = st.columns([1.5, 1])
            df_salidas = df_kardex[df_kardex['QUE PROCESO VA A REALIZAR'] == 'SALIDA']
            consumo_total = df_salidas.groupby('NOMBRE DEL QUIMICO')['CANTIDAD'].sum().reset_index()

            with col_dona:
                st.write("**🍩 Distribución de Consumo**")
                fig_dona = px.pie(consumo_total, values='CANTIDAD', names='NOMBRE DEL QUIMICO', hole=0.6,
                                 color_discrete_sequence=['#2E7D32', '#FBC02D', '#1565C0'], template="plotly_dark")
                fig_dona.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=300)
                st.plotly_chart(fig_dona, use_container_width=True)

            with col_info:
                st.write("**💡 Estado de Bodega**")
                if not consumo_total.empty:
                    st.info("El sistema está monitoreando las salidas diarias para predecir agotamiento de stock.")
                    st.success("Sugerencia: Revisar niveles de Cal el próximo lunes.")

            # --- FILA 3: TABLA DETALLADA (CORREGIDA SIN MATPLOTLIB) ---
            st.markdown("---")
            st.write("**📋 Historial Detallado de Movimientos**")
            
            df_view = df_kardex[['FECHA', 'NOMBRE DEL QUIMICO', 'QUE PROCESO VA A REALIZAR', 'CANTIDAD']].copy()
            df_view = df_view.sort_values('FECHA', ascending=False)
            
            # Usamos st.dataframe directamente con configuración de columnas para el estilo
            st.dataframe(
                df_view,
                column_config={
                    "CANTIDAD": st.column_config.NumberColumn("Cantidad (kg)", format="%.2f"),
                    "QUE PROCESO VA A REALIZAR": st.column_config.TextColumn("Tipo Movimiento")
                },
                use_container_width=True,
                hide_index=True
            )

        else:
            st.warning("No se detectaron datos en la hoja de Químicos.")

except Exception as e:
    st.error(f"Se detectó un error: {e}")
