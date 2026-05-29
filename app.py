import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime
 
# ─────────────────────────────────────────────
# 1. CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="SGA - PTAR - Kenzo Jeans",
    layout="wide",
    page_icon="💧"
)
 
st.markdown("""
<style>
    div.block-container { padding-top: 1rem; padding-bottom: 0rem; }
    [data-testid="stSidebar"] { min-width: 320px; max-width: 350px; }
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1E1E2E;
        border-radius: 8px 8px 0 0;
        padding: 8px 16px;
        color: #aaa;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2E2E4E !important;
        color: white !important;
    }
    div[data-testid="stMetric"] {
        background: #1E1E2E;
        border-radius: 12px;
        padding: 16px;
        border: 1px solid #2E2E4E;
    }
    .card-equipo {
        background: #1E1E2E;
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 20px;
        border-top: 1px solid #333;
        transition: transform 0.2s;
    }
    .card-equipo:hover { transform: translateY(-2px); }
</style>
""", unsafe_allow_html=True)
 
# ─────────────────────────────────────────────
# 2. ENCABEZADO
# ─────────────────────────────────────────────
col_logo, col_titulo = st.columns([1.2, 5])
with col_logo:
    try:
        st.image("logo-white-kenzo.png", use_container_width=True)
    except Exception:
        st.markdown("**KENZO JEANS**")
with col_titulo:
    st.title("SGA - Gestión Integral PTAR - Kenzo Jeans SAS")
 
# ─────────────────────────────────────────────
# 3. URLS DE HOJAS
# ─────────────────────────────────────────────
URL_BASE      = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=0#gid=0"
URL_TRATADA   = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=1338797542#gid=1338797542"
URL_MANTO     = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=746789412#gid=746789412"
URL_QUIMICOS  = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=170562532#gid=170562532"
 
# Nombres EXACTOS de las pestañas en Google Sheets
# ⚠️ Ajusta estos valores si los nombres difieren
WS_BASE     = "vertimiento"
WS_TRATADA  = "agua tratada"
WS_MANTO    = "mantenimiento"
WS_QUIMICOS = "kardex"
 
# ─────────────────────────────────────────────
# 4. FUNCIÓN DE LIMPIEZA UNIFICADA
# ─────────────────────────────────────────────
def limpiar_datos_ptar(df):
    if df is None or df.empty:
        return pd.DataFrame()
 
    df = df.copy()
    df.columns = df.columns.str.strip()
    df = df.loc[:, ~df.columns.duplicated()]
 
    mapeo = {
        'ph': 'ph', 'pH': 'ph', 'PH': 'ph', 'pH Tratada': 'ph',
        'temp': 'temp', 'Temperatura': 'temp', 'Temperatura Tratada': 'temp',
        'sst': 'sst', 'SST': 'sst', 'SST Tratada': 'sst', 'Solidos suspendidos': 'sst',
        'Conductividad': 'cond', 'Conductividad Tratada': 'cond',
        'Caudal': 'caudal', 'Caudal tratado': 'caudal',
        'Fecha': 'fecha', 'fecha': 'fecha', 'Fecha del reporte': 'fecha',
        'Marca temporal': 'fecha_h',
        'Proceso a reportar': 'proceso',
    }
 
    nuevos = {}
    for col in df.columns:
        if col in mapeo:
            target = mapeo[col]
            if target not in nuevos.values():
                nuevos[col] = target
    df = df.rename(columns=nuevos)
 
    for col in ['ph', 'temp', 'sst', 'cond', 'caudal']:
        if col in df.columns:
            df[col] = (
                pd.to_numeric(
                    df[col].astype(str).str.replace(',', '.', regex=False),
                    errors='coerce'
                ).fillna(0)
            )
        else:
            df[col] = 0.0
 
    if 'fecha' not in df.columns and 'fecha_h' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha_h'], errors='coerce').dt.date
    elif 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce').dt.date
 
    # Eliminar filas completamente vacías
    df = df.dropna(how='all')
 
    return df
 
# ─────────────────────────────────────────────
# 5. HELPER: COLORES DE SEMÁFORO
# ─────────────────────────────────────────────
def color_ph(val):
    if 6 <= val <= 9:
        return "#4CAF50"
    elif (5 <= val < 6) or (9 < val <= 10):
        return "#FFEB3B"
    return "#F44336"
 
def color_temp(val):
    if val <= 30:
        return "#4CAF50"
    elif val <= 40:
        return "#FFEB3B"
    return "#F44336"
 
LAYOUT_BASE = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=20, r=20, t=30, b=20),
    font=dict(color='#CCC'),
)
 
# ─────────────────────────────────────────────
# 6. CARGA DE DATOS
# ─────────────────────────────────────────────
try:
    conn = st.connection("gsheets", type=GSheetsConnection)

    # Dataset 1: Vertimientos — SIN spreadsheet= (usa el secrets por defecto)
    df_base_full = limpiar_datos_ptar(conn.read(ttl=0))

    # Dataset 2: Agua Tratada — SIN worksheet=
    try:
        df_tratada = limpiar_datos_ptar(
            conn.read(spreadsheet=URL_TRATADA, ttl=0)
        )
    except Exception as e_t:
        st.sidebar.warning(f"⚠️ Agua Tratada no cargó: {e_t}")
        df_tratada = pd.DataFrame()

    # Dataset 3: Mantenimiento — SIN worksheet=
    try:
        df_manto_raw = conn.read(spreadsheet=URL_MANTO, ttl=0)
        df_manto_raw.columns = df_manto_raw.columns.str.strip()
        df_manto = df_manto_raw.copy()
    except Exception as e_m:
        st.sidebar.warning(f"⚠️ Mantenimiento no cargó: {e_m}")
        df_manto = pd.DataFrame()

    # Dataset 4: Kardex — SIN worksheet=
    try:
        df_kardex = conn.read(spreadsheet=URL_QUIMICOS, ttl=0)
        df_kardex.columns = df_kardex.columns.str.strip().str.upper()
    except Exception as e_k:
        st.sidebar.warning(f"⚠️ Kardex no cargó: {e_k}")
        df_kardex = pd.DataFrame()
 
    # ─────────────────────────────────────────────
    # 7. SIDEBAR — FILTROS
    # ─────────────────────────────────────────────
    with st.sidebar:
        try:
            st.image("logo-white-kenzo.png", use_container_width=True)
            st.markdown("---")
        except Exception:
            pass
 
        st.header("🔍 Filtros Dashboard")
 
        # Copias filtradas (nunca se sobreescribe el original)
        df_vert_filtrado  = df_base_full.copy()
        df_tratada_filtrada = df_tratada.copy()
        df_manto_filtrado = df_manto.copy()
 
        # Filtro de Proceso
        if not df_base_full.empty and 'proceso' in df_base_full.columns:
            procesos = sorted(df_base_full['proceso'].dropna().unique().tolist())
            sel = st.multiselect("Seleccionar Procesos:", procesos, default=procesos)
            df_vert_filtrado = df_vert_filtrado[df_vert_filtrado['proceso'].isin(sel)]
 
        # Filtro de Químico
        filtro_q = st.text_input("Filtrar por Químico:", "")
 
        st.markdown("---")
        st.subheader("📅 Rango de Tiempo")
 
        rango = None
        limite_inf = date(2024, 1, 1)
        limite_sup = date.today()
 
        # Calcular rango máximo entre todos los datasets
        fechas_maximas = []
        if not df_base_full.empty and 'fecha' in df_base_full.columns:
            f_max = df_base_full['fecha'].max()
            if f_max:
                fechas_maximas.append(f_max)
 
        # Buscar columna FECHA en mantenimiento
        col_fecha_m = None
        if not df_manto.empty:
            col_fecha_m = next(
                (c for c in df_manto.columns if c.strip().upper() == 'FECHA'),
                df_manto.columns[0] if len(df_manto.columns) > 0 else None
            )
            if col_fecha_m:
                fechas_m_raw = pd.to_datetime(
                    df_manto[col_fecha_m], dayfirst=True, errors='coerce'
                ).dt.date.dropna()
                if not fechas_m_raw.empty:
                    fechas_maximas.append(fechas_m_raw.max())
 
        if not df_base_full.empty and 'fecha' in df_base_full.columns:
            def_start = df_base_full['fecha'].min() or limite_inf
            def_end   = max(fechas_maximas) if fechas_maximas else limite_sup
 
            rango = st.date_input(
                "Seleccionar fechas:",
                [def_start, def_end],
                min_value=limite_inf,
                max_value=limite_sup,
                key="sidebar_date_range"
            )
 
            if isinstance(rango, (list, tuple)) and len(rango) == 2:
                inicio, fin = rango
 
                # Filtrar vertimientos
                df_vert_filtrado = df_vert_filtrado[
                    (df_vert_filtrado['fecha'] >= inicio) &
                    (df_vert_filtrado['fecha'] <= fin)
                ]
 
                # Filtrar agua tratada
                if not df_tratada_filtrada.empty and 'fecha' in df_tratada_filtrada.columns:
                    df_tratada_filtrada = df_tratada_filtrada[
                        (df_tratada_filtrada['fecha'] >= inicio) &
                        (df_tratada_filtrada['fecha'] <= fin)
                    ]
 
                # Filtrar mantenimiento
                if col_fecha_m and not df_manto_filtrado.empty:
                    df_manto_filtrado[col_fecha_m] = pd.to_datetime(
                        df_manto_filtrado[col_fecha_m], dayfirst=True, errors='coerce'
                    ).dt.date
                    df_manto_filtrado = df_manto_filtrado[
                        (df_manto_filtrado[col_fecha_m] >= inicio) &
                        (df_manto_filtrado[col_fecha_m] <= fin)
                    ]
        else:
            st.info("Carga datos de vertimientos para habilitar filtro de fechas.")
 
        st.markdown("---")
        st.caption("SGA v2.0 · Kenzo Jeans SAS")
 
    # ─────────────────────────────────────────────
    # 8. PESTAÑAS
    # ─────────────────────────────────────────────
    t1, t2, t3, t4 = st.tabs([
        "📊 Dashboard de Vertimientos",
        "🧪 Agua Tratada",
        "🛠️ Mantenimiento",
        "🧪 Consumo de Químicos"
    ])
 
    # ══════════════════════════════════════════
    # TAB 1 — VERTIMIENTOS
    # ══════════════════════════════════════════
    with t1:
        if not df_vert_filtrado.empty:
 
            # ── KPIs ──
            avg_ph   = df_vert_filtrado['ph'].replace(0, np.nan).mean()
            avg_temp = df_vert_filtrado['temp'].replace(0, np.nan).mean()
            avg_sst  = df_vert_filtrado['sst'].replace(0, np.nan).mean()
            n_reg    = len(df_vert_filtrado)
 
            ph_ok   = avg_ph is not None and 6 <= avg_ph <= 9
            temp_ok = avg_temp is not None and avg_temp <= 40
 
            m1, m2, m3, m4 = st.columns(4)
            m1.metric(
                "⚗️ pH Promedio",
                f"{avg_ph:.2f}" if avg_ph else "—",
                delta="✅ NORMA" if ph_ok else "⚠️ ALERTA",
                delta_color="normal" if ph_ok else "inverse"
            )
            m2.metric(
                "🌡️ Temperatura Prom.",
                f"{avg_temp:.1f} °C" if avg_temp else "—",
                delta="✅ NORMAL" if temp_ok else "⚠️ ALTA",
                delta_color="normal" if temp_ok else "inverse"
            )
            m3.metric("🧱 SST Promedio", f"{avg_sst:.1f} mg/L" if avg_sst else "—")
            m4.metric("📋 Registros", n_reg)
 
            st.markdown("---")
 
            # ── FILA 1: pH ──
            col1, col2 = st.columns(2)
 
            with col1:
                st.write("**📈 Histórico de pH (Tintorería)**")
                df_ph = df_vert_filtrado.dropna(subset=['fecha']).sort_values('fecha')
                fig_ph = px.line(df_ph, x='fecha', y='ph', markers=True,
                                 template="plotly_dark",
                                 color_discrete_sequence=['#29B6F6'])
                # Zona de cumplimiento legal
                fig_ph.add_hrect(
                    y0=6, y1=9,
                    fillcolor="rgba(76,175,80,0.10)", line_width=0,
                    annotation_text="Rango legal (6–9)",
                    annotation_position="top left"
                )
                fig_ph.add_hline(y=6, line_dash="dash", line_color="#F44336",
                                 annotation_text="Límite inf (6)")
                fig_ph.add_hline(y=9, line_dash="dash", line_color="#F44336",
                                 annotation_text="Límite sup (9)")
                # Línea de tendencia
                if len(df_ph) > 2:
                    x_n = np.arange(len(df_ph))
                    z   = np.polyfit(x_n, df_ph['ph'].fillna(0), 1)
                    fig_ph.add_scatter(
                        x=df_ph['fecha'], y=np.poly1d(z)(x_n),
                        mode='lines', name='Tendencia',
                        line=dict(color='#FFB300', dash='dot', width=1.5)
                    )
                fig_ph.update_layout(**LAYOUT_BASE)
                st.plotly_chart(fig_ph, use_container_width=True)
 
            with col2:
                st.write("**📊 pH Promedio por Proceso**")
                df_ph_p = (
                    df_vert_filtrado.groupby('proceso')['ph']
                    .mean().reset_index()
                    .sort_values('ph', ascending=False)
                )
                # Color por cumplimiento
                df_ph_p['color'] = df_ph_p['ph'].apply(
                    lambda v: '#4CAF50' if 6 <= v <= 9 else '#F44336'
                )
                fig_ph_p = px.bar(
                    df_ph_p, x='ph', y='proceso', orientation='h',
                    color='color', color_discrete_map='identity',
                    text=df_ph_p['ph'].round(2),
                    template="plotly_dark"
                )
                fig_ph_p.add_vline(x=6, line_dash="dash", line_color="#F44336")
                fig_ph_p.add_vline(x=9, line_dash="dash", line_color="#F44336")
                fig_ph_p.update_traces(textposition='outside', showlegend=False)
                fig_ph_p.update_layout(**LAYOUT_BASE, xaxis_title="pH Promedio",
                                       yaxis_title="")
                st.plotly_chart(fig_ph_p, use_container_width=True)
 
            # ── FILA 2: TEMPERATURA ──
            col3, col4 = st.columns(2)
 
            with col3:
                st.write("**🌡️ Tendencia de Temperatura**")
                df_tmp = df_vert_filtrado.dropna(subset=['fecha']).sort_values('fecha')
                fig_temp = go.Figure()
                # Área base
                fig_temp.add_trace(go.Scatter(
                    x=df_tmp['fecha'], y=df_tmp['temp'],
                    mode='lines+markers',
                    fill='tozeroy',
                    fillcolor='rgba(255,152,0,0.25)',
                    line=dict(color='#FFA726', width=2),
                    name='Temperatura'
                ))
                # Línea de límite máximo
                fig_temp.add_hline(y=40, line_dash="dash", line_color="#F44336",
                                   annotation_text="Máx permisible (40°C)")
                if len(df_tmp) > 2:
                    x_n = np.arange(len(df_tmp))
                    z   = np.polyfit(x_n, df_tmp['temp'].fillna(0), 1)
                    fig_temp.add_trace(go.Scatter(
                        x=df_tmp['fecha'], y=np.poly1d(z)(x_n),
                        mode='lines', name='Tendencia',
                        line=dict(color='#FF7043', dash='dot', width=1.5)
                    ))
                fig_temp.update_layout(
                    template="plotly_dark",
                    xaxis_title="Fecha", yaxis_title="°C",
                    **LAYOUT_BASE
                )
                st.plotly_chart(fig_temp, use_container_width=True)
 
            with col4:
                st.write("**📊 Temperatura Promedio por Proceso**")
                df_temp_p = (
                    df_vert_filtrado.groupby('proceso')['temp']
                    .mean().reset_index()
                    .sort_values('temp', ascending=False)
                )
                df_temp_p['color'] = df_temp_p['temp'].apply(
                    lambda v: '#4CAF50' if v <= 30 else ('#FFEB3B' if v <= 40 else '#F44336')
                )
                fig_tp = px.bar(
                    df_temp_p, x='temp', y='proceso', orientation='h',
                    color='color', color_discrete_map='identity',
                    text=df_temp_p['temp'].round(1),
                    template="plotly_dark"
                )
                fig_tp.add_vline(x=40, line_dash="dash", line_color="#F44336",
                                 annotation_text="Límite (40°C)")
                fig_tp.update_traces(textposition='outside', showlegend=False)
                fig_tp.update_layout(**LAYOUT_BASE, xaxis_title="°C", yaxis_title="")
                st.plotly_chart(fig_tp, use_container_width=True)
 
            # ── FILA 3: SST ──
            col5, col6 = st.columns([1, 1.5])
 
            with col5:
                st.write("**🍩 SST Promedio por Proceso**")
                df_sst_p = (
                    df_vert_filtrado.groupby('proceso')['sst']
                    .mean().reset_index()
                )
                fig_sst = px.pie(
                    df_sst_p, values='sst', names='proceso', hole=0.55,
                    template="plotly_dark",
                    color_discrete_sequence=['#29B6F6', '#FFA726', '#66BB6A', '#CE93D8']
                )
                fig_sst.update_traces(textinfo='label+percent')
                fig_sst.update_layout(**LAYOUT_BASE)
                st.plotly_chart(fig_sst, use_container_width=True)
 
            with col6:
                st.write("**📈 Evolución de SST en el Tiempo**")
                df_sst_t = df_vert_filtrado.dropna(subset=['fecha']).sort_values('fecha')
                fig_sst_t = px.line(
                    df_sst_t, x='fecha', y='sst',
                    color='proceso' if 'proceso' in df_sst_t.columns else None,
                    markers=True, template="plotly_dark",
                    color_discrete_sequence=['#29B6F6', '#FFA726', '#66BB6A', '#CE93D8']
                )
                fig_sst_t.update_layout(**LAYOUT_BASE,
                                        xaxis_title="Fecha",
                                        yaxis_title="SST (mg/L)")
                st.plotly_chart(fig_sst_t, use_container_width=True)
 
            # ── TABLA DE DATOS (corregida: muestra vertimientos, no mantenimiento) ──
            st.markdown("---")
            with st.expander("📄 Ver tabla de datos de vertimientos"):
                cols_mostrar = [c for c in df_vert_filtrado.columns
                                if c not in ['fecha_h']]
                st.dataframe(
                    df_vert_filtrado[cols_mostrar].sort_values('fecha', ascending=False),
                    use_container_width=True,
                    hide_index=True
                )
 
        else:
            st.warning("⚠️ Ajusta los filtros para ver datos de vertimientos.")
 
    # ══════════════════════════════════════════
    # TAB 2 — AGUA TRATADA
    # ══════════════════════════════════════════
    with t2:
        st.subheader("🧪 Monitoreo de Agua Tratada")
 
        if not df_tratada_filtrada.empty:
 
            avg_ph_t    = df_tratada_filtrada['ph'].replace(0, np.nan).mean()
            avg_temp_t  = df_tratada_filtrada['temp'].replace(0, np.nan).mean()
            avg_sst_sal = df_tratada_filtrada['sst'].replace(0, np.nan).mean()
            total_caudal = df_tratada_filtrada['caudal'].replace(0, np.nan).sum()
            sst_ent     = df_base_full['sst'].replace(0, np.nan).mean() \
                          if not df_base_full.empty else None
 
            remocion = 0.0
            if sst_ent and sst_ent > 0 and avg_sst_sal is not None:
                remocion = max(0, (1 - avg_sst_sal / sst_ent) * 100) \
                           if avg_sst_sal > 0 else 100.0
 
            ph_ok_t   = avg_ph_t is not None and 6 <= avg_ph_t <= 9
            temp_ok_t = avg_temp_t is not None and avg_temp_t <= 40
 
            # ── KPIs ──
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("💧 SST Salida (Prom)",
                      f"{avg_sst_sal:.1f} mg/L" if avg_sst_sal else "—",
                      delta=f"⬇️ {remocion:.1f}% Eficiencia")
            c2.metric("⚗️ pH Salida",
                      f"{avg_ph_t:.2f}" if avg_ph_t else "—",
                      delta="✅ OK" if ph_ok_t else "⚠️ FUERA",
                      delta_color="normal" if ph_ok_t else "inverse")
            c3.metric("🌡️ Temp. Salida",
                      f"{avg_temp_t:.1f} °C" if avg_temp_t else "—",
                      delta="✅ ESTABLE" if temp_ok_t else "⚠️ ALTA",
                      delta_color="normal" if temp_ok_t else "inverse")
            c4.metric("📦 Volumen Tratado",
                      f"{total_caudal:.1f} m³" if total_caudal else "—")
 
            st.markdown("---")
 
            # ── FILA 1: pH y Temperatura ──
            col_a, col_b = st.columns(2)
 
            with col_a:
                st.write("**📈 pH del Agua Tratada**")
                df_ph_t = df_tratada_filtrada.dropna(subset=['fecha']).sort_values('fecha')
                fig_ph_t = px.line(df_ph_t, x='fecha', y='ph', markers=True,
                                   template="plotly_dark",
                                   color_discrete_sequence=['#00C853'])
                fig_ph_t.add_hrect(y0=6, y1=9,
                                   fillcolor="rgba(0,200,83,0.08)", line_width=0,
                                   annotation_text="Rango legal (6–9)",
                                   annotation_position="top left")
                fig_ph_t.add_hline(y=6, line_dash="dash", line_color="#F44336",
                                   annotation_text="Mín (6)")
                fig_ph_t.add_hline(y=9, line_dash="dash", line_color="#F44336",
                                   annotation_text="Máx (9)")
                if len(df_ph_t) > 2:
                    x_n = np.arange(len(df_ph_t))
                    z   = np.polyfit(x_n, df_ph_t['ph'].fillna(0), 1)
                    fig_ph_t.add_scatter(
                        x=df_ph_t['fecha'], y=np.poly1d(z)(x_n),
                        mode='lines', name='Tendencia',
                        line=dict(color='#FFB300', dash='dot', width=1.5)
                    )
                fig_ph_t.update_layout(**LAYOUT_BASE)
                st.plotly_chart(fig_ph_t, use_container_width=True)
 
            with col_b:
                st.write("**🌡️ Temperatura de Salida**")
                fig_temp_t = go.Figure()
                df_temp_t_sorted = df_tratada_filtrada.dropna(subset=['fecha']).sort_values('fecha')
                fig_temp_t.add_trace(go.Scatter(
                    x=df_temp_t_sorted['fecha'], y=df_temp_t_sorted['temp'],
                    mode='lines+markers', fill='tozeroy',
                    fillcolor='rgba(255,167,38,0.25)',
                    line=dict(color='#FFA726', width=2),
                    name='Temperatura'
                ))
                fig_temp_t.add_hline(y=40, line_dash="dash", line_color="#F44336",
                                     annotation_text="Máx permisible (40°C)")
                fig_temp_t.update_layout(
                    template="plotly_dark",
                    xaxis_title="Fecha", yaxis_title="°C",
                    **LAYOUT_BASE
                )
                st.plotly_chart(fig_temp_t, use_container_width=True)
 
            # ── FILA 2: Eficiencia SST y Caudal ──
            col_c, col_d = st.columns(2)
 
            with col_c:
                st.write("**💧 Remoción de Sólidos (Entrada vs. Salida)**")
                if sst_ent is not None and avg_sst_sal is not None:
                    df_comp = pd.DataFrame({
                        'Etapa':      ['Entrada (Crudo)', 'Salida (Tratada)'],
                        'SST (mg/L)': [round(sst_ent, 1), round(avg_sst_sal, 1)]
                    })
                    fig_rem = px.bar(
                        df_comp, x='SST (mg/L)', y='Etapa', orientation='h',
                        color='Etapa', text='SST (mg/L)',
                        color_discrete_map={
                            'Entrada (Crudo)':  '#78909C',
                            'Salida (Tratada)': '#00E676'
                        },
                        template="plotly_dark"
                    )
                    fig_rem.update_traces(texttemplate='%{text:.1f} mg/L',
                                         textposition='outside', showlegend=False)
                    fig_rem.update_layout(**LAYOUT_BASE, yaxis_title="")
                    st.plotly_chart(fig_rem, use_container_width=True)
                    st.info(f"**Eficiencia de remoción: {remocion:.1f}%** "
                            f"({sst_ent:.1f} → {avg_sst_sal:.1f} mg/L)")
                else:
                    st.warning("Sin datos de SST para calcular eficiencia.")
 
            with col_d:
                st.write("**📊 Volumen de Agua Tratada por Día**")
                df_cau = df_tratada_filtrada[
                    df_tratada_filtrada['caudal'] > 0
                ].dropna(subset=['fecha']).sort_values('fecha')
 
                if not df_cau.empty:
                    fig_cau = px.bar(
                        df_cau, x='fecha', y='caudal',
                        template="plotly_dark",
                        color_discrete_sequence=['#29B6F6'],
                        text='caudal'
                    )
                    if len(df_cau) > 2:
                        x_n = np.arange(len(df_cau))
                        z   = np.polyfit(x_n, df_cau['caudal'].values, 1)
                        fig_cau.add_scatter(
                            x=df_cau['fecha'], y=np.poly1d(z)(x_n),
                            mode='lines', name='Tendencia',
                            line=dict(color='#FF7043', dash='dash')
                        )
                    fig_cau.update_traces(
                        texttemplate='%{text:.1f}', textposition='outside',
                        selector=dict(type='bar')
                    )
                    fig_cau.update_layout(**LAYOUT_BASE,
                                         xaxis_title="Fecha",
                                         yaxis_title="m³")
                    st.plotly_chart(fig_cau, use_container_width=True)
                else:
                    st.info("Sin registros de caudal > 0 en el periodo.")
 
            # ── FILA 3: Conductividad (si existe) ──
            if df_tratada_filtrada['cond'].sum() > 0:
                st.markdown("---")
                st.write("**⚡ Conductividad del Agua Tratada**")
                fig_cond = px.line(
                    df_tratada_filtrada.dropna(subset=['fecha']).sort_values('fecha'),
                    x='fecha', y='cond', markers=True,
                    template="plotly_dark",
                    color_discrete_sequence=['#CE93D8']
                )
                fig_cond.update_layout(**LAYOUT_BASE,
                                       xaxis_title="Fecha",
                                       yaxis_title="Conductividad (µS/cm)")
                st.plotly_chart(fig_cond, use_container_width=True)
 
            # ── Tabla ──
            with st.expander("📄 Ver tabla de datos de agua tratada"):
                st.dataframe(
                    df_tratada_filtrada.sort_values('fecha', ascending=False),
                    use_container_width=True, hide_index=True
                )
 
        else:
            st.warning("⚠️ No se cargaron datos de agua tratada.")
            st.markdown("""
            **Verifica:**
            - Que el nombre de la pestaña en Google Sheets coincida con `WS_TRATADA` (arriba en el código)
            - Que la cuenta de servicio tenga acceso al Spreadsheet
            - Que la hoja tenga columnas: `Fecha`, `pH Tratada`, `Temperatura Tratada`, `SST Tratada`, `Caudal tratado`
            """)
 
    # ══════════════════════════════════════════
    # TAB 3 — MANTENIMIENTO
    # ══════════════════════════════════════════
    with t3:
        st.subheader("🛠️ Estado de Equipos - Kenzo Jeans")
 
        if not df_manto_filtrado.empty:
            # Normalizar columnas
            df_m = df_manto_filtrado.copy()
            df_m.columns = df_m.columns.str.strip().str.upper()
 
            col_fecha_m2 = next(
                (c for c in df_m.columns if c.strip().upper() == 'FECHA'),
                df_m.columns[0]
            )
            if df_m[col_fecha_m2].dtype == object:
                df_m[col_fecha_m2] = pd.to_datetime(
                    df_m[col_fecha_m2], dayfirst=True, errors='coerce'
                ).dt.date
 
            if 'SALUD' in df_m.columns:
                df_m['SALUD'] = pd.to_numeric(df_m['SALUD'], errors='coerce').fillna(0)
 
            # ── KPIs de resumen ──
            if 'SALUD' in df_m.columns:
                salud_prom = df_m['SALUD'].mean()
                equi_crit  = (df_m.groupby('EQUIPO')['SALUD'].last() < 6).sum() \
                             if 'EQUIPO' in df_m.columns else 0
                equi_prev  = ((df_m.groupby('EQUIPO')['SALUD'].last() >= 6) &
                              (df_m.groupby('EQUIPO')['SALUD'].last() < 8)).sum() \
                             if 'EQUIPO' in df_m.columns else 0
                equi_ok    = (df_m.groupby('EQUIPO')['SALUD'].last() >= 8).sum() \
                             if 'EQUIPO' in df_m.columns else 0
 
                km1, km2, km3, km4 = st.columns(4)
                km1.metric("💚 Equipos Óptimos",    equi_ok)
                km2.metric("🟡 Equipos Preventivos", equi_prev)
                km3.metric("🔴 Equipos Críticos",   equi_crit)
                km4.metric("📊 Salud Promedio",      f"{salud_prom:.1f}/10")
                st.markdown("---")
 
            # ── Tarjetas por equipo ──
            if 'EQUIPO' in df_m.columns:
                equipos = df_m['EQUIPO'].dropna().unique()
                cols_eq = st.columns(min(3, len(equipos)))
 
                for i, eq in enumerate(equipos):
                    ult = df_m[df_m['EQUIPO'] == eq].sort_values(col_fecha_m2).iloc[-1]
                    val_s    = ult['SALUD']
                    fecha_v  = ult[col_fecha_m2]
                    observ   = ult.get('OBSERVACIONES', ult.get('OBSERVACION', ''))
 
                    color     = "#4CAF50" if val_s >= 8 else ("#FFEB3B" if val_s >= 6 else "#F44336")
                    desc      = "ÓPTIMO"     if val_s >= 8 else ("PREVENTIVO" if val_s >= 6 else "CRÍTICO")
                    icono     = "✅" if val_s >= 8 else ("⚠️" if val_s >= 6 else "🚨")
                    barra_w   = int(val_s * 10)
 
                    with cols_eq[i % 3]:
                        st.markdown(f"""
                        <div class="card-equipo" style="border-left: 10px solid {color};">
                            <h4 style="margin:0; color:white;">{icono} {eq}</h4>
                            <p style="color:{color}; font-weight:bold; margin:4px 0 8px 0; font-size:12px;">{desc}</p>
                            <h2 style="margin:0 0 8px 0; color:{color};">📈 {val_s}/10</h2>
                            <div style="background:#333; border-radius:6px; height:8px; width:100%;">
                                <div style="background:{color}; border-radius:6px; height:8px; width:{barra_w}%;"></div>
                            </div>
                            <small style="color:#888; display:block; margin-top:8px;">
                                Última revisión: {fecha_v}
                            </small>
                            {"<small style='color:#AAA;'>" + str(observ)[:80] + "…</small>" if pd.notna(observ) and str(observ).strip() else ""}
                        </div>
                        """, unsafe_allow_html=True)
 
            st.markdown("---")
 
            # ── Heatmap + Alertas ──
            col_v1, col_v2 = st.columns([2, 1])
 
            with col_v1:
                st.write("**🌡️ Mapa de Salud por Equipo y Fecha**")
                if 'EQUIPO' in df_m.columns and 'SALUD' in df_m.columns:
                    df_pivot = df_m.pivot_table(
                        index='EQUIPO',
                        columns=col_fecha_m2,
                        values='SALUD',
                        aggfunc='last'
                    ).fillna(0)
                    df_pivot.columns = [str(c) for c in df_pivot.columns]
 
                    fig_heat = px.imshow(
                        df_pivot,
                        labels=dict(x="Fecha", y="Equipo", color="Salud"),
                        color_continuous_scale=['#F44336', '#FFEB3B', '#4CAF50'],
                        zmin=0, zmax=10,
                        aspect="auto",
                        template="plotly_dark",
                        text_auto=True
                    )
                    fig_heat.update_layout(
                        margin=dict(l=10, r=10, t=10, b=10),
                        height=300,
                        paper_bgcolor='rgba(0,0,0,0)'
                    )
                    st.plotly_chart(fig_heat, use_container_width=True)
 
            with col_v2:
                st.write("**📢 Alertas de Mantenimiento**")
                if 'EQUIPO' in df_m.columns and 'SALUD' in df_m.columns:
                    pendientes = (
                        df_m[df_m['SALUD'] < 7]
                        .sort_values(col_fecha_m2, ascending=False)
                        .drop_duplicates('EQUIPO')
                    )
                    if not pendientes.empty:
                        for _, row in pendientes.iterrows():
                            nivel = "🚨 CRÍTICO" if row['SALUD'] < 6 else "⚠️ PREVENTIVO"
                            st.warning(f"**{row['EQUIPO']}** — {nivel}\n\n"
                                       f"Salud: {row['SALUD']}/10")
                    else:
                        st.success("✅ Todos los equipos operan en rangos seguros.")
 
            # ── Evolución de salud ──
            if 'EQUIPO' in df_m.columns and 'SALUD' in df_m.columns:
                st.markdown("---")
                st.write("**📈 Evolución de Salud por Equipo**")
                fig_evo = px.line(
                    df_m.sort_values(col_fecha_m2),
                    x=col_fecha_m2, y='SALUD',
                    color='EQUIPO', markers=True,
                    template="plotly_dark",
                    color_discrete_sequence=['#4CAF50', '#FFA726', '#29B6F6',
                                             '#CE93D8', '#F44336', '#FFD54F']
                )
                fig_evo.add_hrect(y0=0, y1=6,
                                  fillcolor="rgba(244,67,54,0.07)", line_width=0,
                                  annotation_text="Zona crítica")
                fig_evo.add_hrect(y0=6, y1=8,
                                  fillcolor="rgba(255,235,59,0.07)", line_width=0,
                                  annotation_text="Zona preventiva")
                fig_evo.update_layout(**LAYOUT_BASE, height=350,
                                      yaxis=dict(range=[0, 10.5]),
                                      xaxis_title="Fecha",
                                      yaxis_title="Salud (0–10)")
                st.plotly_chart(fig_evo, use_container_width=True)
 
            # ── Bitácora ──
            with st.expander("📝 Ver historial completo de intervenciones"):
                cols_ok = [c for c in df_m.columns if c not in ['MARCA TEMPORAL']]
                st.dataframe(
                    df_m[cols_ok].sort_values(col_fecha_m2, ascending=False),
                    use_container_width=True, hide_index=True
                )
 
        else:
            st.warning("⚠️ No se cargaron datos de mantenimiento. "
                       "Verifica el nombre de la pestaña en `WS_MANTO`.")
 
    # ══════════════════════════════════════════
    # TAB 4 — CONSUMO DE QUÍMICOS
    # ══════════════════════════════════════════
    with t4:
        st.subheader("📦 Gestión de Inventarios y Consumo - Kenzo Jeans")
 
        STOCK_INICIAL = {
            "SULFATO DE ALUMINIO": 119,
            "CAL":                  79,
            "POLIMERO":             24.118
        }
 
        if not df_kardex.empty:
            # Limpieza
            df_k = df_kardex.copy()
            df_k['CANTIDAD'] = pd.to_numeric(
                df_k['CANTIDAD'].astype(str)
                .str.replace(',', '.', regex=False)
                .str.replace(r'[^0-9.]', '', regex=True),
                errors='coerce'
            ).fillna(0)
            df_k['FECHA'] = pd.to_datetime(
                df_k['FECHA'], dayfirst=True, errors='coerce'
            ).dt.date
 
            # Filtrar por rango si existe
            df_k_periodo = df_k.copy()
            if isinstance(rango, (list, tuple)) and len(rango) == 2:
                inicio, fin = rango
                df_k_periodo = df_k_periodo[
                    (df_k_periodo['FECHA'] >= inicio) &
                    (df_k_periodo['FECHA'] <= fin)
                ]
 
            # Aplica filtro de químico de sidebar
            if filtro_q:
                df_k_periodo = df_k_periodo[
                    df_k_periodo['NOMBRE DEL QUIMICO'].astype(str)
                    .str.contains(filtro_q, case=False, na=False)
                ]
 
            # ── KPIs de Stock actual ──
            df_k['NETO'] = df_k.apply(
                lambda x: x['CANTIDAD']
                if str(x.get('QUE PROCESO VA A REALIZAR', '')).upper() == 'ENTRADA'
                else -x['CANTIDAD'],
                axis=1
            )
            resumen_inv = df_k.groupby('NOMBRE DEL QUIMICO')['NETO'].sum().to_dict()
 
            st.markdown("#### 📦 Stock Actual")
            ck1, ck2, ck3 = st.columns(3)
            cols_k = [ck1, ck2, ck3]
 
            for i, (prod, stock_ini) in enumerate(STOCK_INICIAL.items()):
                actual = stock_ini + resumen_inv.get(prod, 0)
                alerta = "⚠️ REABASTECER" if actual < 20 else "✅ STOCK OK"
                cols_k[i].metric(
                    prod, f"{actual:.1f} kg",
                    delta=alerta,
                    delta_color="inverse" if actual < 20 else "normal"
                )
 
            # Barra de stock visual
            st.markdown("**Nivel de stock relativo:**")
            col_bars = st.columns(3)
            for i, (prod, stock_ini) in enumerate(STOCK_INICIAL.items()):
                actual  = stock_ini + resumen_inv.get(prod, 0)
                pct     = min(100, max(0, actual / stock_ini * 100))
                color_s = "#4CAF50" if pct > 40 else ("#FFEB3B" if pct > 20 else "#F44336")
                with col_bars[i]:
                    st.markdown(f"""
                    <div style="background:#1E1E2E; border-radius:8px; padding:8px;">
                        <small style="color:#AAA;">{prod[:20]}</small><br>
                        <div style="background:#333; border-radius:4px; height:10px; margin-top:4px;">
                            <div style="background:{color_s}; border-radius:4px; height:10px; width:{pct:.0f}%;"></div>
                        </div>
                        <small style="color:{color_s};">{pct:.0f}% del stock inicial</small>
                    </div>
                    """, unsafe_allow_html=True)
 
            st.markdown("---")
 
            # ── Consumo en el periodo ──
            st.markdown("#### 📊 Consumo en el Periodo Seleccionado")
            df_salidas_p = df_k_periodo[
                df_k_periodo['QUE PROCESO VA A REALIZAR'].astype(str).str.upper() == 'SALIDA'
            ]
            consumo_periodo = df_salidas_p.groupby('NOMBRE DEL QUIMICO')['CANTIDAD'].sum().to_dict()
 
            cs1, cs2, cs3 = st.columns(3)
            quimicos_obj = ["SULFATO DE ALUMINIO", "CAL", "POLIMERO"]
            cols_sal = [cs1, cs2, cs3]
 
            for i, q in enumerate(quimicos_obj):
                total_sal  = consumo_periodo.get(q, 0.0)
                n_reg_q    = len(df_salidas_p[df_salidas_p['NOMBRE DEL QUIMICO'] == q])
                cols_sal[i].metric(
                    label=f"Salidas: {q}",
                    value=f"{total_sal:.2f} kg",
                    delta=f"{n_reg_q} registros",
                    delta_color="normal"
                )
 
            st.markdown("---")
 
            # ── FILA: Dona + Tendencia temporal ──
            col_dona, col_tend = st.columns([1, 1.5])
 
            with col_dona:
                st.write("**🍩 Distribución de Consumo Total**")
                df_salidas_all = df_k[
                    df_k['QUE PROCESO VA A REALIZAR'].astype(str).str.upper() == 'SALIDA'
                ]
                consumo_total = (
                    df_salidas_all.groupby('NOMBRE DEL QUIMICO')['CANTIDAD']
                    .sum().reset_index()
                )
                fig_dona = px.pie(
                    consumo_total, values='CANTIDAD', names='NOMBRE DEL QUIMICO',
                    hole=0.6,
                    color_discrete_sequence=['#2E7D32', '#FBC02D', '#1565C0'],
                    template="plotly_dark"
                )
                fig_dona.update_traces(textinfo='label+percent+value',
                                       texttemplate='%{label}<br>%{percent}<br>%{value:.1f} kg')
                fig_dona.update_layout(**LAYOUT_BASE, height=320)
                st.plotly_chart(fig_dona, use_container_width=True)
 
            with col_tend:
                st.write("**📈 Consumo Acumulado en el Tiempo**")
                df_sal_t = df_k_periodo[
                    df_k_periodo['QUE PROCESO VA A REALIZAR'].astype(str).str.upper() == 'SALIDA'
                ].dropna(subset=['FECHA'])
 
                if not df_sal_t.empty:
                    df_sal_t = df_sal_t.sort_values('FECHA')
                    df_sal_t['ACUMULADO'] = (
                        df_sal_t.groupby('NOMBRE DEL QUIMICO')['CANTIDAD'].cumsum()
                    )
                    fig_tend = px.line(
                        df_sal_t, x='FECHA', y='ACUMULADO',
                        color='NOMBRE DEL QUIMICO',
                        markers=True, template="plotly_dark",
                        color_discrete_sequence=['#4CAF50', '#FBC02D', '#29B6F6'],
                        labels={'ACUMULADO': 'Consumo Acumulado (kg)', 'FECHA': 'Fecha'}
                    )
                    fig_tend.update_layout(**LAYOUT_BASE, height=320)
                    st.plotly_chart(fig_tend, use_container_width=True)
                else:
                    st.info("Sin registros de salida en el periodo.")
 
            # ── Proyección de agotamiento ──
            st.markdown("---")
            st.write("**🔮 Proyección de Agotamiento de Stock**")
 
            proj_cols = st.columns(3)
            for i, (prod, stock_ini) in enumerate(STOCK_INICIAL.items()):
                actual = stock_ini + resumen_inv.get(prod, 0)
                df_sal_prod = df_k[
                    (df_k['NOMBRE DEL QUIMICO'] == prod) &
                    (df_k['QUE PROCESO VA A REALIZAR'].astype(str).str.upper() == 'SALIDA')
                ].dropna(subset=['FECHA'])
 
                with proj_cols[i]:
                    if not df_sal_prod.empty and len(df_sal_prod) >= 2:
                        consumo_diario = df_sal_prod['CANTIDAD'].sum()
                        primer_dia  = df_sal_prod['FECHA'].min()
                        ultimo_dia  = df_sal_prod['FECHA'].max()
                        dias_rango  = max(1, (ultimo_dia - primer_dia).days)
                        tasa_diaria = consumo_diario / dias_rango
 
                        if tasa_diaria > 0:
                            dias_rest = int(actual / tasa_diaria)
                            color_p   = "#4CAF50" if dias_rest > 30 else \
                                        ("#FFEB3B" if dias_rest > 10 else "#F44336")
                            st.markdown(f"""
                            <div style="background:#1E1E2E; border-radius:12px; padding:16px;
                                        border-left:6px solid {color_p};">
                                <small style="color:#AAA;">{prod}</small><br>
                                <b style="color:{color_p}; font-size:1.4rem;">{dias_rest} días</b><br>
                                <small style="color:#888;">stock restante estimado</small><br>
                                <small style="color:#AAA;">Tasa: {tasa_diaria:.2f} kg/día</small>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.info(f"{prod}: sin consumo detectado.")
                    else:
                        st.info(f"{prod}: insuficientes datos para proyectar.")
 
            # ── Tabla detallada ──
            st.markdown("---")
            with st.expander("📋 Historial detallado de movimientos"):
                cols_vista = [c for c in ['FECHA', 'NOMBRE DEL QUIMICO',
                                          'QUE PROCESO VA A REALIZAR', 'CANTIDAD']
                              if c in df_k_periodo.columns]
                st.dataframe(
                    df_k_periodo[cols_vista].sort_values('FECHA', ascending=False),
                    column_config={
                        "CANTIDAD": st.column_config.NumberColumn(
                            "Cantidad (kg)", format="%.2f"
                        ),
                        "QUE PROCESO VA A REALIZAR": st.column_config.TextColumn(
                            "Tipo Movimiento"
                        )
                    },
                    use_container_width=True,
                    hide_index=True
                )
 
        else:
            st.warning("⚠️ No se detectaron datos en la hoja de Químicos. "
                       "Verifica el nombre de la pestaña en `WS_QUIMICOS`.")
 
except Exception as e:
    st.error(f"❌ Error general en la aplicación: {e}")
    st.exception(e)
