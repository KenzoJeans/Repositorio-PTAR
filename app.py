import io
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

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
# 2. MÓDULO PDF (integrado directamente)
# ─────────────────────────────────────────────
AZUL_OSCURO = colors.HexColor("#0D1B2A")
AZUL_MEDIO  = colors.HexColor("#1B3A5C")
AZUL_CLARO  = colors.HexColor("#2E7CB8")
VERDE_OK    = colors.HexColor("#2E7D32")
VERDE_CLARO = colors.HexColor("#4CAF50")
AMARILLO    = colors.HexColor("#F9A825")
ROJO        = colors.HexColor("#C62828")
GRIS_CLARO  = colors.HexColor("#F5F7FA")
GRIS_MEDIO  = colors.HexColor("#B0BEC5")
BLANCO      = colors.white
NEGRO       = colors.HexColor("#1A1A1A")
W, H        = A4


def _safe_pdf(val, decimales=2, sufijo=""):
    try:
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return "—"
        return f"{float(val):.{decimales}f}{sufijo}"
    except Exception:
        return str(val)


def _semaforo_pdf(val, verde_min, verde_max, invert=False):
    try:
        v = float(val)
        if not invert:
            return (VERDE_CLARO, "CUMPLE") if verde_min <= v <= verde_max else \
                   (AMARILLO, "REVISAR") if abs(v - verde_min) <= 1 or abs(v - verde_max) <= 1 else \
                   (ROJO, "ALERTA")
        else:
            return (VERDE_CLARO, "CUMPLE") if v <= verde_max else (ROJO, "ALERTA")
    except Exception:
        return (GRIS_MEDIO, "S/D")


def _estilos_pdf():
    return {
        "titulo_doc": ParagraphStyle("titulo_doc", fontSize=22,
            fontName="Helvetica-Bold", textColor=BLANCO, alignment=TA_CENTER, spaceAfter=4),
        "subtitulo_doc": ParagraphStyle("subtitulo_doc", fontSize=11,
            fontName="Helvetica", textColor=colors.HexColor("#90CAF9"),
            alignment=TA_CENTER, spaceAfter=2),
        "seccion": ParagraphStyle("seccion", fontSize=11, fontName="Helvetica-Bold",
            textColor=AZUL_CLARO, spaceBefore=12, spaceAfter=6),
        "normal": ParagraphStyle("normal", fontSize=9, fontName="Helvetica",
            textColor=NEGRO, spaceAfter=3),
        "normal_c": ParagraphStyle("normal_c", fontSize=9, fontName="Helvetica",
            textColor=NEGRO, alignment=TA_CENTER),
        "kpi_valor": ParagraphStyle("kpi_valor", fontSize=18,
            fontName="Helvetica-Bold", textColor=AZUL_CLARO, alignment=TA_CENTER),
        "kpi_label": ParagraphStyle("kpi_label", fontSize=7, fontName="Helvetica",
            textColor=GRIS_MEDIO, alignment=TA_CENTER),
        "pie": ParagraphStyle("pie", fontSize=7, fontName="Helvetica",
            textColor=GRIS_MEDIO, alignment=TA_CENTER),
    }


def _seccion_header(titulo, estilos):
    return [
        HRFlowable(width="100%", thickness=1.5, color=AZUL_CLARO, spaceAfter=4),
        Paragraph(f"◆  {titulo}", estilos["seccion"]),
    ]


def _tabla_kpi_pdf(datos, estilos):
    n     = len(datos)
    col_w = (W - 40 * mm) / n
    enc, vals, ests = [], [], []
    for d in datos:
        enc.append(Paragraph(d["label"], estilos["kpi_label"]))
        vals.append(Paragraph(
            f"{d['valor']} <font size='8'>{d.get('unidad','')}</font>",
            estilos["kpi_valor"]))
        c_e = d.get("color_estado", GRIS_MEDIO)
        st_style = ParagraphStyle("_e", fontSize=7, fontName="Helvetica-Bold",
                                   textColor=c_e, alignment=TA_CENTER)
        ests.append(Paragraph(f"● {d.get('estado','')}", st_style))
    t = Table([enc, vals, ests], colWidths=[col_w] * n)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), GRIS_CLARO),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor("#DDE3EA")),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
    ]))
    return t


def _tabla_datos_pdf(filas, col_widths, estilos):
    if not filas or len(filas) < 2:
        return Paragraph("Sin datos.", estilos["normal"])
    header = [Paragraph(str(c), ParagraphStyle("th", fontSize=8,
               fontName="Helvetica-Bold", textColor=BLANCO,
               alignment=TA_CENTER)) for c in filas[0]]
    body = [[Paragraph(str(c) if c is not None else "—", estilos["normal_c"])
             for c in row] for row in filas[1:]]
    t = Table([header] + body, colWidths=col_widths)
    cmds = [
        ("BACKGROUND",    (0, 0), (-1, 0),  AZUL_MEDIO),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#CFD8DC")),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("FONTSIZE",      (0, 1), (-1, -1), 8),
    ]
    for i in range(len(body)):
        if i % 2 == 0:
            cmds.append(("BACKGROUND", (0, i+1), (-1, i+1),
                         colors.HexColor("#EEF3F8")))
    t.setStyle(TableStyle(cmds))
    return t


def _barra_pdf(valor, maximo, color_b, ancho=120*mm, alto=5*mm):
    pct = min(1.0, max(0.0, valor / maximo)) if maximo > 0 else 0
    wr  = ancho * pct
    wv  = ancho - wr
    if wr > 0 and wv > 0:
        celdas, widths = [["", ""]], [wr, wv]
        cmds = [("BACKGROUND", (0,0),(0,0), color_b),
                ("BACKGROUND", (1,0),(1,0), colors.HexColor("#D0D7DE"))]
    elif wr == 0:
        celdas, widths = [[""]], [ancho]
        cmds = [("BACKGROUND", (0,0),(-1,-1), colors.HexColor("#D0D7DE"))]
    else:
        celdas, widths = [[""]], [ancho]
        cmds = [("BACKGROUND", (0,0),(-1,-1), color_b)]
    cmds += [("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),
             ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)]
    t = Table(celdas, colWidths=widths, rowHeights=[alto])
    t.setStyle(TableStyle(cmds))
    return t


def generar_reporte_pdf(df_vert, df_tratada, df_manto, df_kardex,
                        rango_fechas=None):
    buffer = io.BytesIO()
    hoy    = datetime.now()
    doc    = SimpleDocTemplate(buffer, pagesize=A4,
                leftMargin=18*mm, rightMargin=18*mm,
                topMargin=12*mm, bottomMargin=16*mm,
                title="Reporte PTAR - Kenzo Jeans SAS")
    estilos = _estilos_pdf()
    story   = []

    fecha_str = hoy.strftime("%d de %B de %Y — %H:%M h")
    rango_txt = "Período completo"
    if rango_fechas and len(rango_fechas) == 2:
        rango_txt = (f"{rango_fechas[0].strftime('%d/%m/%Y')} "
                     f"al {rango_fechas[1].strftime('%d/%m/%Y')}")

    # ── Banner ──
    banner = Table([[
        Paragraph("SISTEMA DE GESTIÓN AMBIENTAL", estilos["subtitulo_doc"]),
        Paragraph("REPORTE TÉCNICO PTAR",          estilos["titulo_doc"]),
        Paragraph("Kenzo Jeans SAS",               estilos["subtitulo_doc"]),
    ]], colWidths=[W - 36*mm])
    banner.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), AZUL_OSCURO),
        ("TOPPADDING",    (0,0),(-1,-1), 14),
        ("BOTTOMPADDING", (0,0),(-1,-1), 14),
        ("LEFTPADDING",   (0,0),(-1,-1), 20),
        ("RIGHTPADDING",  (0,0),(-1,-1), 20),
    ]))
    story.append(banner)
    story.append(Spacer(1, 6*mm))

    # ── Metadatos ──
    meta = Table([[
        Paragraph(f"📅 <b>Generado:</b> {fecha_str}", estilos["normal"]),
        Paragraph(f"🗓️ <b>Período:</b> {rango_txt}",  estilos["normal"]),
        Paragraph(f"📋 <b>Registros:</b> {len(df_vert)}", estilos["normal"]),
    ]], colWidths=[(W - 36*mm) / 3] * 3)
    meta.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor("#EEF3F8")),
        ("GRID",          (0,0),(-1,-1), 0.5, colors.HexColor("#CFD8DC")),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
    ]))
    story.append(meta)
    story.append(Spacer(1, 8*mm))

    # ── 1. Vertimientos ──
    story += _seccion_header("1. Parámetros de Vertimientos (Tintorería)", estilos)
    if not df_vert.empty:
        avg_ph   = df_vert['ph'].replace(0, float('nan')).mean()
        avg_temp = df_vert['temp'].replace(0, float('nan')).mean()
        avg_sst  = df_vert['sst'].replace(0, float('nan')).mean()
        c_ph,   e_ph   = _semaforo_pdf(avg_ph,   6,  9)
        c_temp, e_temp = _semaforo_pdf(avg_temp,  0, 40, invert=True)
        c_sst,  e_sst  = _semaforo_pdf(avg_sst,   0, 100, invert=True)
        story.append(KeepTogether([_tabla_kpi_pdf([
            {"label":"pH Promedio",       "valor":_safe_pdf(avg_ph),    "unidad":"pH",      "color_estado":c_ph,   "estado":e_ph},
            {"label":"Temperatura Prom.", "valor":_safe_pdf(avg_temp,1),"unidad":"°C",      "color_estado":c_temp, "estado":e_temp},
            {"label":"SST Promedio",      "valor":_safe_pdf(avg_sst,1), "unidad":"mg/L",    "color_estado":c_sst,  "estado":e_sst},
            {"label":"Total Registros",   "valor":str(len(df_vert)),    "unidad":"muestras","color_estado":AZUL_CLARO,"estado":"PERÍODO"},
        ], estilos)]))
        story.append(Spacer(1, 5*mm))
        if 'proceso' in df_vert.columns:
            df_proc = df_vert.groupby('proceso').agg(
                pH_prom=('ph','mean'), Temp_prom=('temp','mean'),
                SST_prom=('sst','mean'), Registros=('ph','count')
            ).reset_index()
            cw = [(W-36*mm)/5]*5
            filas = [["Proceso","pH Prom.","Temp. (°C)","SST (mg/L)","Registros"]]
            for _, r in df_proc.iterrows():
                filas.append([str(r['proceso']), _safe_pdf(r['pH_prom']),
                              _safe_pdf(r['Temp_prom'],1), _safe_pdf(r['SST_prom'],1),
                              str(int(r['Registros']))])
            story.append(_tabla_datos_pdf(filas, cw, estilos))
    else:
        story.append(Paragraph("Sin datos de vertimientos.", estilos["normal"]))
    story.append(Spacer(1, 6*mm))

    # ── 2. Agua Tratada ──
    story += _seccion_header("2. Agua Tratada — Eficiencia del Sistema", estilos)
    if not df_tratada.empty:
        avg_ph_t    = df_tratada['ph'].replace(0, float('nan')).mean()
        avg_temp_t  = df_tratada['temp'].replace(0, float('nan')).mean()
        avg_sst_sal = df_tratada['sst'].replace(0, float('nan')).mean()
        total_cau   = df_tratada['caudal'].replace(0, float('nan')).sum()
        sst_ent     = df_vert['sst'].replace(0, float('nan')).mean() if not df_vert.empty else None
        remocion    = 0.0
        if sst_ent and sst_ent > 0 and avg_sst_sal and avg_sst_sal >= 0:
            remocion = max(0,(1 - avg_sst_sal/sst_ent)*100) if avg_sst_sal > 0 else 100.0
        c_ph_t,  e_ph_t  = _semaforo_pdf(avg_ph_t,  6, 9)
        c_tmp_t, e_tmp_t = _semaforo_pdf(avg_temp_t, 0, 40, invert=True)
        c_rem,   e_rem   = _semaforo_pdf(remocion,  70, 100)
        story.append(KeepTogether([_tabla_kpi_pdf([
            {"label":"pH Salida",      "valor":_safe_pdf(avg_ph_t),    "unidad":"pH",  "color_estado":c_ph_t,  "estado":e_ph_t},
            {"label":"Temp. Salida",   "valor":_safe_pdf(avg_temp_t,1),"unidad":"°C",  "color_estado":c_tmp_t, "estado":e_tmp_t},
            {"label":"SST Salida",     "valor":_safe_pdf(avg_sst_sal,1),"unidad":"mg/L","color_estado":AZUL_CLARO,"estado":"SALIDA"},
            {"label":"Eficiencia SST", "valor":_safe_pdf(remocion,1),  "unidad":"%",   "color_estado":c_rem,   "estado":e_rem},
        ], estilos)]))
        story.append(Spacer(1, 4*mm))
        story.append(Paragraph(
            f"Eficiencia de remoción: <b>{_safe_pdf(remocion,1)}%</b> "
            f"({_safe_pdf(sst_ent,1)} → {_safe_pdf(avg_sst_sal,1)} mg/L SST)",
            estilos["normal"]))
        story.append(Spacer(1, 1*mm))
        color_rem = VERDE_CLARO if remocion >= 70 else (AMARILLO if remocion >= 40 else ROJO)
        story.append(_barra_pdf(remocion, 100, color_rem, ancho=W-36*mm))
        if total_cau and not pd.isna(total_cau):
            story.append(Spacer(1,3*mm))
            story.append(Paragraph(
                f"Volumen total tratado: <b>{_safe_pdf(total_cau,1)} m³</b>",
                estilos["normal"]))
    else:
        story.append(Paragraph("Sin datos de agua tratada.", estilos["normal"]))
    story.append(Spacer(1, 6*mm))

    # ── 3. Mantenimiento ──
    story += _seccion_header("3. Estado de Equipos — Mantenimiento", estilos)
    if not df_manto.empty:
        df_m = df_manto.copy()
        df_m.columns = df_m.columns.str.strip().str.upper()
        if 'SALUD' in df_m.columns:
            df_m['SALUD'] = pd.to_numeric(df_m['SALUD'], errors='coerce').fillna(0)
        if 'EQUIPO' in df_m.columns and 'SALUD' in df_m.columns:
            res_eq  = df_m.groupby('EQUIPO')['SALUD'].last().reset_index()
            n_ok    = (res_eq['SALUD'] >= 8).sum()
            n_prev  = ((res_eq['SALUD'] >= 6) & (res_eq['SALUD'] < 8)).sum()
            n_crit  = (res_eq['SALUD'] < 6).sum()
            prom_s  = res_eq['SALUD'].mean()
            story.append(KeepTogether([_tabla_kpi_pdf([
                {"label":"Equipos Óptimos",    "valor":str(n_ok),           "unidad":"equipos","color_estado":VERDE_CLARO,"estado":"ÓPTIMO"},
                {"label":"Equipos Preventivos","valor":str(n_prev),         "unidad":"equipos","color_estado":AMARILLO,   "estado":"PREVENTIVO"},
                {"label":"Equipos Críticos",   "valor":str(n_crit),         "unidad":"equipos","color_estado":ROJO,       "estado":"CRÍTICO"},
                {"label":"Salud Promedio",     "valor":_safe_pdf(prom_s,1), "unidad":"/10",   "color_estado":AZUL_CLARO, "estado":"FLOTA"},
            ], estilos)]))
            story.append(Spacer(1, 4*mm))
            col_f = next((c for c in df_m.columns if 'FECHA' in c), df_m.columns[0])
            cw_eq = [(W-36*mm)*f for f in [0.35,0.15,0.20,0.30]]
            filas_eq = [["Equipo","Salud","Estado","Últ. Revisión"]]
            for _, row in res_eq.sort_values('SALUD').iterrows():
                s   = row['SALUD']
                est = "ÓPTIMO" if s>=8 else ("PREVENTIVO" if s>=6 else "CRÍTICO")
                ult = df_m[df_m['EQUIPO']==row['EQUIPO']][col_f].iloc[-1] \
                      if col_f in df_m.columns else "—"
                filas_eq.append([str(row['EQUIPO']), f"{s}/10", est, str(ult)])
            story.append(_tabla_datos_pdf(filas_eq, cw_eq, estilos))
    else:
        story.append(Paragraph("Sin datos de mantenimiento.", estilos["normal"]))
    story.append(Spacer(1, 6*mm))

    # ── 4. Químicos ──
    story += _seccion_header("4. Consumo e Inventario de Químicos", estilos)
    STOCK_INI = {"SULFATO DE ALUMINIO":119, "CAL":79, "POLIMERO":24.118}
    if not df_kardex.empty:
        df_k = df_kardex.copy()
        df_k.columns = df_k.columns.str.strip().str.upper()
        if 'CANTIDAD' in df_k.columns:
            df_k['CANTIDAD'] = pd.to_numeric(
                df_k['CANTIDAD'].astype(str).str.replace(',','.', regex=False)
                .str.replace(r'[^0-9.]','',regex=True), errors='coerce').fillna(0)
        proc_col = next((c for c in df_k.columns if 'PROCESO' in c or 'TIPO' in c), None)
        nom_col  = next((c for c in df_k.columns if 'QUIMICO' in c or 'NOMBRE' in c), None)
        if proc_col and nom_col:
            df_k['NETO'] = df_k.apply(
                lambda x: x['CANTIDAD'] if str(x[proc_col]).upper()=='ENTRADA'
                else -x['CANTIDAD'], axis=1)
            res_inv  = df_k.groupby(nom_col)['NETO'].sum().to_dict()
            df_sal   = df_k[df_k[proc_col].astype(str).str.upper()=='SALIDA']
            cons_t   = df_sal.groupby(nom_col)['CANTIDAD'].sum().to_dict()
            cw_q     = [(W-36*mm)*f for f in [0.32,0.17,0.18,0.17,0.16]]
            filas_q  = [["Químico","Stock Inicial","Consumo","Stock Actual","Estado"]]
            for prod, ini in STOCK_INI.items():
                actual  = ini + res_inv.get(prod, 0)
                consumo = cons_t.get(prod, 0)
                filas_q.append([prod, f"{ini:.1f} kg", f"{consumo:.1f} kg",
                                 f"{actual:.1f} kg",
                                 "⚠ REABASTECER" if actual < 20 else "✓ OK"])
            story.append(_tabla_datos_pdf(filas_q, cw_q, estilos))
            story.append(Spacer(1, 4*mm))
            story.append(Paragraph("Nivel de stock relativo:", estilos["normal"]))
            story.append(Spacer(1, 2*mm))
            for prod, ini in STOCK_INI.items():
                actual  = ini + res_inv.get(prod, 0)
                pct     = min(1.0, max(0.0, actual/ini))
                color_b = VERDE_CLARO if pct>0.4 else (AMARILLO if pct>0.2 else ROJO)
                fila_b  = [[
                    Paragraph(f"<b>{prod}</b>", estilos["normal"]),
                    _barra_pdf(actual, ini, color_b, ancho=90*mm, alto=5*mm),
                    Paragraph(f"{pct*100:.0f}%  ({actual:.1f} kg)", estilos["normal"]),
                ]]
                tb = Table(fila_b, colWidths=[(W-36*mm)*0.35, 90*mm, (W-36*mm)*0.20])
                tb.setStyle(TableStyle([
                    ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                    ("TOPPADDING",(0,0),(-1,-1),3),
                    ("BOTTOMPADDING",(0,0),(-1,-1),3),
                    ("LEFTPADDING",(0,0),(-1,-1),0),
                    ("RIGHTPADDING",(0,0),(-1,-1),4),
                ]))
                story.append(tb)
    else:
        story.append(Paragraph("Sin datos de químicos.", estilos["normal"]))
    story.append(Spacer(1, 8*mm))

    # ── 5. Declaración ──
    story += _seccion_header("5. Declaración de Conformidad", estilos)
    story.append(Paragraph(
        "El presente reporte ha sido generado automáticamente por el Sistema de "
        "Gestión Ambiental (SGA) de Kenzo Jeans SAS a partir de los datos registrados "
        "en la Planta de Tratamiento de Aguas Residuales (PTAR). Los valores consignados "
        "corresponden al período indicado y tienen carácter informativo de seguimiento "
        "interno del programa de cumplimiento ambiental.",
        estilos["normal"]))
    story.append(Spacer(1, 10*mm))
    firma = Table([[
        Table([[""], [Paragraph("Responsable PTAR",  ParagraphStyle("f1",fontSize=9,alignment=TA_CENTER))],
                      [Paragraph("Kenzo Jeans SAS",  ParagraphStyle("f2",fontSize=7,textColor=GRIS_MEDIO,alignment=TA_CENTER))]],
               colWidths=[65*mm]),
        Spacer(1,1),
        Table([[""], [Paragraph("Director Ambiental", ParagraphStyle("f3",fontSize=9,alignment=TA_CENTER))],
                      [Paragraph("Kenzo Jeans SAS",   ParagraphStyle("f4",fontSize=7,textColor=GRIS_MEDIO,alignment=TA_CENTER))]],
               colWidths=[65*mm]),
    ]], colWidths=[65*mm, 20*mm, 65*mm])
    firma.setStyle(TableStyle([
        ("LINEABOVE",(0,0),(0,0),0.8,AZUL_MEDIO),
        ("LINEABOVE",(2,0),(2,0),0.8,AZUL_MEDIO),
        ("TOPPADDING",(0,0),(-1,-1),6),
        ("ALIGN",(0,0),(-1,-1),"CENTER"),
    ]))
    story.append(firma)

    def _pie(canvas_obj, doc_obj):
        canvas_obj.saveState()
        canvas_obj.setFont("Helvetica", 7)
        canvas_obj.setFillColor(GRIS_MEDIO)
        canvas_obj.drawString(18*mm, 10*mm,
            f"SGA — PTAR Kenzo Jeans SAS  |  {hoy.strftime('%d/%m/%Y %H:%M')}  |  Uso interno")
        canvas_obj.drawRightString(W-18*mm, 10*mm, f"Página {doc_obj.page}")
        canvas_obj.setStrokeColor(AZUL_CLARO)
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(18*mm, 12*mm, W-18*mm, 12*mm)
        canvas_obj.restoreState()

    doc.build(story, onFirstPage=_pie, onLaterPages=_pie)
    return buffer.getvalue()


# ─────────────────────────────────────────────
# 3. ENCABEZADO
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
# 4. URLS DE HOJAS
# ─────────────────────────────────────────────
URL_BASE     = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=0#gid=0"
URL_TRATADA  = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=1338797542#gid=1338797542"
URL_MANTO    = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=746789412#gid=746789412"
URL_QUIMICOS = "https://docs.google.com/spreadsheets/d/12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek/edit?resourcekey=&gid=170562532#gid=170562532"

# ─────────────────────────────────────────────
# 5. FUNCIÓN DE LIMPIEZA
# ─────────────────────────────────────────────
def limpiar_datos_ptar(df):
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    df.columns = df.columns.str.strip()
    df = df.loc[:, ~df.columns.duplicated()]
    mapeo = {
        'ph':'ph','pH':'ph','PH':'ph','pH Tratada':'ph',
        'temp':'temp','Temperatura':'temp','Temperatura Tratada':'temp',
        'sst':'sst','SST':'sst','SST Tratada':'sst','Solidos suspendidos':'sst',
        'Conductividad':'cond','Conductividad Tratada':'cond',
        'Caudal':'caudal','Caudal tratado':'caudal',
        'Fecha':'fecha','fecha':'fecha','Fecha del reporte':'fecha',
        'Marca temporal':'fecha_h','Proceso a reportar':'proceso',
    }
    nuevos = {}
    for col in df.columns:
        if col in mapeo:
            target = mapeo[col]
            if target not in nuevos.values():
                nuevos[col] = target
    df = df.rename(columns=nuevos)
    for col in ['ph','temp','sst','cond','caudal']:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(',','.', regex=False),
                errors='coerce').fillna(0)
        else:
            df[col] = 0.0
    if 'fecha' not in df.columns and 'fecha_h' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha_h'], errors='coerce').dt.date
    elif 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce').dt.date
    df = df.dropna(how='all')
    return df

LAYOUT_BASE = dict(
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=20, r=20, t=30, b=20), font=dict(color='#CCC'),
)

# ─────────────────────────────────────────────
# 6. CARGA DE DATOS
# ─────────────────────────────────────────────
try:
    conn = st.connection("gsheets", type=GSheetsConnection)

    df_base_full = limpiar_datos_ptar(conn.read(ttl=0))

    try:
        df_tratada = limpiar_datos_ptar(conn.read(spreadsheet=URL_TRATADA, ttl=0))
    except Exception as e_t:
        st.sidebar.warning(f"⚠️ Agua Tratada no cargó: {e_t}")
        df_tratada = pd.DataFrame()

    try:
        df_manto_raw = conn.read(spreadsheet=URL_MANTO, ttl=0)
        df_manto_raw.columns = df_manto_raw.columns.str.strip()
        df_manto = df_manto_raw.copy()
    except Exception as e_m:
        st.sidebar.warning(f"⚠️ Mantenimiento no cargó: {e_m}")
        df_manto = pd.DataFrame()

    try:
        df_kardex = conn.read(spreadsheet=URL_QUIMICOS, ttl=0)
        df_kardex.columns = df_kardex.columns.str.strip().str.upper()
    except Exception as e_k:
        st.sidebar.warning(f"⚠️ Kardex no cargó: {e_k}")
        df_kardex = pd.DataFrame()

    # ─────────────────────────────────────────────
    # 7. SIDEBAR
    # ─────────────────────────────────────────────
    with st.sidebar:
        try:
            st.image("logo-white-kenzo.png", use_container_width=True)
            st.markdown("---")
        except Exception:
            pass

        st.header("🔍 Filtros Dashboard")

        df_vert_filtrado    = df_base_full.copy()
        df_tratada_filtrada = df_tratada.copy()
        df_manto_filtrado   = df_manto.copy()

        if not df_base_full.empty and 'proceso' in df_base_full.columns:
            procesos = sorted(df_base_full['proceso'].dropna().unique().tolist())
            sel = st.multiselect("Seleccionar Procesos:", procesos, default=procesos)
            df_vert_filtrado = df_vert_filtrado[df_vert_filtrado['proceso'].isin(sel)]

        filtro_q = st.text_input("Filtrar por Químico:", "")

        st.markdown("---")
        st.subheader("📅 Rango de Tiempo")

        rango      = None
        limite_inf = date(2024, 1, 1)
        limite_sup = date.today()

        fechas_maximas = []
        if not df_base_full.empty and 'fecha' in df_base_full.columns:
            f_max = df_base_full['fecha'].max()
            if f_max:
                fechas_maximas.append(f_max)

        col_fecha_m = None
        if not df_manto.empty:
            col_fecha_m = next(
                (c for c in df_manto.columns if c.strip().upper() == 'FECHA'),
                df_manto.columns[0] if len(df_manto.columns) > 0 else None)
            if col_fecha_m:
                fechas_m_raw = pd.to_datetime(
                    df_manto[col_fecha_m], dayfirst=True, errors='coerce'
                ).dt.date.dropna()
                if not fechas_m_raw.empty:
                    fechas_maximas.append(fechas_m_raw.max())

        if not df_base_full.empty and 'fecha' in df_base_full.columns:
            def_start = df_base_full['fecha'].min() or limite_inf
            def_end   = max(fechas_maximas) if fechas_maximas else limite_sup
            rango = st.date_input("Seleccionar fechas:", [def_start, def_end],
                                  min_value=limite_inf, max_value=limite_sup,
                                  key="sidebar_date_range")
            if isinstance(rango, (list, tuple)) and len(rango) == 2:
                inicio, fin = rango
                df_vert_filtrado = df_vert_filtrado[
                    (df_vert_filtrado['fecha'] >= inicio) &
                    (df_vert_filtrado['fecha'] <= fin)]
                if not df_tratada_filtrada.empty and 'fecha' in df_tratada_filtrada.columns:
                    df_tratada_filtrada = df_tratada_filtrada[
                        (df_tratada_filtrada['fecha'] >= inicio) &
                        (df_tratada_filtrada['fecha'] <= fin)]
                if col_fecha_m and not df_manto_filtrado.empty:
                    df_manto_filtrado[col_fecha_m] = pd.to_datetime(
                        df_manto_filtrado[col_fecha_m], dayfirst=True, errors='coerce').dt.date
                    df_manto_filtrado = df_manto_filtrado[
                        (df_manto_filtrado[col_fecha_m] >= inicio) &
                        (df_manto_filtrado[col_fecha_m] <= fin)]
        else:
            st.info("Carga datos de vertimientos para habilitar filtro de fechas.")

        # ── Exportar PDF ──
        st.markdown("---")
        st.subheader("📄 Exportar Reporte")
        if st.button("🖨️ Generar certificado PDF", use_container_width=True):
            with st.spinner("Generando reporte..."):
                try:
                    pdf_bytes = generar_reporte_pdf(
                        df_vert      = df_vert_filtrado,
                        df_tratada   = df_tratada_filtrada,
                        df_manto     = df_manto_filtrado,
                        df_kardex    = df_kardex,
                        rango_fechas = rango if isinstance(rango, (list, tuple)) else None,
                    )
                    st.download_button(
                        label     = "⬇️ Descargar PDF",
                        data      = pdf_bytes,
                        file_name = f"Reporte_PTAR_Kenzo_{date.today()}.pdf",
                        mime      = "application/pdf",
                        use_container_width=True,
                    )
                except Exception as e_pdf:
                    st.error(f"Error generando PDF: {e_pdf}")

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
            avg_ph   = df_vert_filtrado['ph'].replace(0, np.nan).mean()
            avg_temp = df_vert_filtrado['temp'].replace(0, np.nan).mean()
            avg_sst  = df_vert_filtrado['sst'].replace(0, np.nan).mean()
            n_reg    = len(df_vert_filtrado)
            ph_ok    = avg_ph is not None and 6 <= avg_ph <= 9
            temp_ok  = avg_temp is not None and avg_temp <= 40

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("⚗️ pH Promedio",
                      f"{avg_ph:.2f}" if avg_ph else "—",
                      delta="✅ NORMA" if ph_ok else "⚠️ ALERTA",
                      delta_color="normal" if ph_ok else "inverse")
            m2.metric("🌡️ Temperatura Prom.",
                      f"{avg_temp:.1f} °C" if avg_temp else "—",
                      delta="✅ NORMAL" if temp_ok else "⚠️ ALTA",
                      delta_color="normal" if temp_ok else "inverse")
            m3.metric("🧱 SST Promedio", f"{avg_sst:.1f} mg/L" if avg_sst else "—")
            m4.metric("📋 Registros", n_reg)
            st.markdown("---")

            col1, col2 = st.columns(2)
            with col1:
                st.write("**📈 Histórico de pH (Tintorería)**")
                df_ph = df_vert_filtrado.dropna(subset=['fecha']).sort_values('fecha')
                fig_ph = px.line(df_ph, x='fecha', y='ph', markers=True,
                                 template="plotly_dark",
                                 color_discrete_sequence=['#29B6F6'])
                fig_ph.add_hrect(y0=6, y1=9, fillcolor="rgba(76,175,80,0.10)",
                                 line_width=0, annotation_text="Rango legal (6–9)",
                                 annotation_position="top left")
                fig_ph.add_hline(y=6, line_dash="dash", line_color="#F44336",
                                 annotation_text="Límite inf (6)")
                fig_ph.add_hline(y=9, line_dash="dash", line_color="#F44336",
                                 annotation_text="Límite sup (9)")
                if len(df_ph) > 2:
                    x_n = np.arange(len(df_ph))
                    z   = np.polyfit(x_n, df_ph['ph'].fillna(0), 1)
                    fig_ph.add_scatter(x=df_ph['fecha'], y=np.poly1d(z)(x_n),
                                       mode='lines', name='Tendencia',
                                       line=dict(color='#FFB300',dash='dot',width=1.5))
                fig_ph.update_layout(**LAYOUT_BASE)
                st.plotly_chart(fig_ph, use_container_width=True)

            with col2:
                st.write("**📊 pH Promedio por Proceso**")
                df_ph_p = (df_vert_filtrado.groupby('proceso')['ph']
                           .mean().reset_index().sort_values('ph', ascending=False))
                df_ph_p['color'] = df_ph_p['ph'].apply(
                    lambda v: '#4CAF50' if 6<=v<=9 else '#F44336')
                fig_ph_p = px.bar(df_ph_p, x='ph', y='proceso', orientation='h',
                                  color='color', color_discrete_map='identity',
                                  text=df_ph_p['ph'].round(2), template="plotly_dark")
                fig_ph_p.add_vline(x=6, line_dash="dash", line_color="#F44336")
                fig_ph_p.add_vline(x=9, line_dash="dash", line_color="#F44336")
                fig_ph_p.update_traces(textposition='outside', showlegend=False)
                fig_ph_p.update_layout(**LAYOUT_BASE, xaxis_title="pH Promedio", yaxis_title="")
                st.plotly_chart(fig_ph_p, use_container_width=True)

            col3, col4 = st.columns(2)
            with col3:
                st.write("**🌡️ Tendencia de Temperatura**")
                df_tmp = df_vert_filtrado.dropna(subset=['fecha']).sort_values('fecha')
                fig_temp = go.Figure()
                fig_temp.add_trace(go.Scatter(
                    x=df_tmp['fecha'], y=df_tmp['temp'],
                    mode='lines+markers', fill='tozeroy',
                    fillcolor='rgba(255,152,0,0.25)',
                    line=dict(color='#FFA726', width=2), name='Temperatura'))
                fig_temp.add_hline(y=40, line_dash="dash", line_color="#F44336",
                                   annotation_text="Máx permisible (40°C)")
                if len(df_tmp) > 2:
                    x_n = np.arange(len(df_tmp))
                    z   = np.polyfit(x_n, df_tmp['temp'].fillna(0), 1)
                    fig_temp.add_trace(go.Scatter(
                        x=df_tmp['fecha'], y=np.poly1d(z)(x_n),
                        mode='lines', name='Tendencia',
                        line=dict(color='#FF7043', dash='dot', width=1.5)))
                fig_temp.update_layout(template="plotly_dark",
                                       xaxis_title="Fecha", yaxis_title="°C",
                                       **LAYOUT_BASE)
                st.plotly_chart(fig_temp, use_container_width=True)

            with col4:
                st.write("**📊 Temperatura Promedio por Proceso**")
                df_temp_p = (df_vert_filtrado.groupby('proceso')['temp']
                             .mean().reset_index().sort_values('temp', ascending=False))
                df_temp_p['color'] = df_temp_p['temp'].apply(
                    lambda v: '#4CAF50' if v<=30 else ('#FFEB3B' if v<=40 else '#F44336'))
                fig_tp = px.bar(df_temp_p, x='temp', y='proceso', orientation='h',
                                color='color', color_discrete_map='identity',
                                text=df_temp_p['temp'].round(1), template="plotly_dark")
                fig_tp.add_vline(x=40, line_dash="dash", line_color="#F44336",
                                 annotation_text="Límite (40°C)")
                fig_tp.update_traces(textposition='outside', showlegend=False)
                fig_tp.update_layout(**LAYOUT_BASE, xaxis_title="°C", yaxis_title="")
                st.plotly_chart(fig_tp, use_container_width=True)

            col5, col6 = st.columns([1, 1.5])
            with col5:
                st.write("**🍩 SST Promedio por Proceso**")
                df_sst_p = df_vert_filtrado.groupby('proceso')['sst'].mean().reset_index()
                fig_sst = px.pie(df_sst_p, values='sst', names='proceso', hole=0.55,
                                 template="plotly_dark",
                                 color_discrete_sequence=['#29B6F6','#FFA726','#66BB6A','#CE93D8'])
                fig_sst.update_traces(textinfo='label+percent')
                fig_sst.update_layout(**LAYOUT_BASE)
                st.plotly_chart(fig_sst, use_container_width=True)

            with col6:
                st.write("**📈 Evolución de SST en el Tiempo**")
                df_sst_t = df_vert_filtrado.dropna(subset=['fecha']).sort_values('fecha')
                fig_sst_t = px.line(df_sst_t, x='fecha', y='sst',
                                    color='proceso' if 'proceso' in df_sst_t.columns else None,
                                    markers=True, template="plotly_dark",
                                    color_discrete_sequence=['#29B6F6','#FFA726','#66BB6A','#CE93D8'])
                fig_sst_t.update_layout(**LAYOUT_BASE, xaxis_title="Fecha", yaxis_title="SST (mg/L)")
                st.plotly_chart(fig_sst_t, use_container_width=True)

            st.markdown("---")
            with st.expander("📄 Ver tabla de datos de vertimientos"):
                cols_mostrar = [c for c in df_vert_filtrado.columns if c not in ['fecha_h']]
                st.dataframe(df_vert_filtrado[cols_mostrar].sort_values('fecha', ascending=False),
                             use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ Ajusta los filtros para ver datos de vertimientos.")

    # ══════════════════════════════════════════
    # TAB 2 — AGUA TRATADA
    # ══════════════════════════════════════════
    with t2:
        st.subheader("🧪 Monitoreo de Agua Tratada")
        if not df_tratada_filtrada.empty:
            avg_ph_t     = df_tratada_filtrada['ph'].replace(0, np.nan).mean()
            avg_temp_t   = df_tratada_filtrada['temp'].replace(0, np.nan).mean()
            avg_sst_sal  = df_tratada_filtrada['sst'].replace(0, np.nan).mean()
            total_caudal = df_tratada_filtrada['caudal'].replace(0, np.nan).sum()
            sst_ent      = df_base_full['sst'].replace(0, np.nan).mean() \
                           if not df_base_full.empty else None
            remocion = 0.0
            if sst_ent and sst_ent > 0 and avg_sst_sal is not None:
                remocion = max(0,(1-avg_sst_sal/sst_ent)*100) if avg_sst_sal > 0 else 100.0
            ph_ok_t   = avg_ph_t is not None and 6 <= avg_ph_t <= 9
            temp_ok_t = avg_temp_t is not None and avg_temp_t <= 40

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

            col_a, col_b = st.columns(2)
            with col_a:
                st.write("**📈 pH del Agua Tratada**")
                df_ph_t = df_tratada_filtrada.dropna(subset=['fecha']).sort_values('fecha')
                fig_ph_t = px.line(df_ph_t, x='fecha', y='ph', markers=True,
                                   template="plotly_dark",
                                   color_discrete_sequence=['#00C853'])
                fig_ph_t.add_hrect(y0=6, y1=9, fillcolor="rgba(0,200,83,0.08)",
                                   line_width=0, annotation_text="Rango legal (6–9)",
                                   annotation_position="top left")
                fig_ph_t.add_hline(y=6, line_dash="dash", line_color="#F44336",
                                   annotation_text="Mín (6)")
                fig_ph_t.add_hline(y=9, line_dash="dash", line_color="#F44336",
                                   annotation_text="Máx (9)")
                if len(df_ph_t) > 2:
                    x_n = np.arange(len(df_ph_t))
                    z   = np.polyfit(x_n, df_ph_t['ph'].fillna(0), 1)
                    fig_ph_t.add_scatter(x=df_ph_t['fecha'], y=np.poly1d(z)(x_n),
                                         mode='lines', name='Tendencia',
                                         line=dict(color='#FFB300',dash='dot',width=1.5))
                fig_ph_t.update_layout(**LAYOUT_BASE)
                st.plotly_chart(fig_ph_t, use_container_width=True)

            with col_b:
                st.write("**🌡️ Temperatura de Salida**")
                fig_temp_t = go.Figure()
                df_tt = df_tratada_filtrada.dropna(subset=['fecha']).sort_values('fecha')
                fig_temp_t.add_trace(go.Scatter(
                    x=df_tt['fecha'], y=df_tt['temp'],
                    mode='lines+markers', fill='tozeroy',
                    fillcolor='rgba(255,167,38,0.25)',
                    line=dict(color='#FFA726', width=2), name='Temperatura'))
                fig_temp_t.add_hline(y=40, line_dash="dash", line_color="#F44336",
                                     annotation_text="Máx permisible (40°C)")
                fig_temp_t.update_layout(template="plotly_dark",
                                         xaxis_title="Fecha", yaxis_title="°C",
                                         **LAYOUT_BASE)
                st.plotly_chart(fig_temp_t, use_container_width=True)

            col_c, col_d = st.columns(2)
            with col_c:
                st.write("**💧 Remoción de Sólidos (Entrada vs. Salida)**")
                if sst_ent is not None and avg_sst_sal is not None:
                    df_comp = pd.DataFrame({
                        'Etapa':      ['Entrada (Crudo)', 'Salida (Tratada)'],
                        'SST (mg/L)': [round(sst_ent,1), round(avg_sst_sal,1)]})
                    fig_rem = px.bar(df_comp, x='SST (mg/L)', y='Etapa', orientation='h',
                                     color='Etapa', text='SST (mg/L)',
                                     color_discrete_map={'Entrada (Crudo)':'#78909C',
                                                         'Salida (Tratada)':'#00E676'},
                                     template="plotly_dark")
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
                df_cau = df_tratada_filtrada[df_tratada_filtrada['caudal']>0]\
                         .dropna(subset=['fecha']).sort_values('fecha')
                if not df_cau.empty:
                    fig_cau = px.bar(df_cau, x='fecha', y='caudal',
                                     template="plotly_dark",
                                     color_discrete_sequence=['#29B6F6'], text='caudal')
                    if len(df_cau) > 2:
                        x_n = np.arange(len(df_cau))
                        z   = np.polyfit(x_n, df_cau['caudal'].values, 1)
                        fig_cau.add_scatter(x=df_cau['fecha'], y=np.poly1d(z)(x_n),
                                            mode='lines', name='Tendencia',
                                            line=dict(color='#FF7043', dash='dash'))
                    fig_cau.update_traces(texttemplate='%{text:.1f}',
                                          textposition='outside',
                                          selector=dict(type='bar'))
                    fig_cau.update_layout(**LAYOUT_BASE, xaxis_title="Fecha", yaxis_title="m³")
                    st.plotly_chart(fig_cau, use_container_width=True)
                else:
                    st.info("Sin registros de caudal > 0 en el periodo.")

            if df_tratada_filtrada['cond'].sum() > 0:
                st.markdown("---")
                st.write("**⚡ Conductividad del Agua Tratada**")
                fig_cond = px.line(
                    df_tratada_filtrada.dropna(subset=['fecha']).sort_values('fecha'),
                    x='fecha', y='cond', markers=True, template="plotly_dark",
                    color_discrete_sequence=['#CE93D8'])
                fig_cond.update_layout(**LAYOUT_BASE, xaxis_title="Fecha",
                                       yaxis_title="Conductividad (µS/cm)")
                st.plotly_chart(fig_cond, use_container_width=True)

            with st.expander("📄 Ver tabla de datos de agua tratada"):
                st.dataframe(df_tratada_filtrada.sort_values('fecha', ascending=False),
                             use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ No se cargaron datos de agua tratada.")
            st.markdown("""
            **Verifica:**
            - Que el nombre de la pestaña en Google Sheets coincida con la URL configurada
            - Que la cuenta de servicio tenga acceso al Spreadsheet
            - Que la hoja tenga columnas: `Fecha`, `pH Tratada`, `Temperatura Tratada`, `SST Tratada`, `Caudal tratado`
            """)

    # ══════════════════════════════════════════
    # TAB 3 — MANTENIMIENTO
    # ══════════════════════════════════════════
    with t3:
        st.subheader("🛠️ Estado de Equipos - Kenzo Jeans")
        if not df_manto_filtrado.empty:
            df_m = df_manto_filtrado.copy()
            df_m.columns = df_m.columns.str.strip().str.upper()
            col_fecha_m2 = next((c for c in df_m.columns if c.strip().upper()=='FECHA'),
                                df_m.columns[0])
            if df_m[col_fecha_m2].dtype == object:
                df_m[col_fecha_m2] = pd.to_datetime(
                    df_m[col_fecha_m2], dayfirst=True, errors='coerce').dt.date
            if 'SALUD' in df_m.columns:
                df_m['SALUD'] = pd.to_numeric(df_m['SALUD'], errors='coerce').fillna(0)

            if 'SALUD' in df_m.columns:
                salud_prom = df_m['SALUD'].mean()
                equi_crit  = (df_m.groupby('EQUIPO')['SALUD'].last()<6).sum() \
                             if 'EQUIPO' in df_m.columns else 0
                equi_prev  = ((df_m.groupby('EQUIPO')['SALUD'].last()>=6) &
                              (df_m.groupby('EQUIPO')['SALUD'].last()<8)).sum() \
                             if 'EQUIPO' in df_m.columns else 0
                equi_ok    = (df_m.groupby('EQUIPO')['SALUD'].last()>=8).sum() \
                             if 'EQUIPO' in df_m.columns else 0
                km1,km2,km3,km4 = st.columns(4)
                km1.metric("💚 Equipos Óptimos",     equi_ok)
                km2.metric("🟡 Equipos Preventivos", equi_prev)
                km3.metric("🔴 Equipos Críticos",    equi_crit)
                km4.metric("📊 Salud Promedio",       f"{salud_prom:.1f}/10")
                st.markdown("---")

            if 'EQUIPO' in df_m.columns:
                equipos = df_m['EQUIPO'].dropna().unique()
                cols_eq = st.columns(min(3, len(equipos)))
                for i, eq in enumerate(equipos):
                    ult     = df_m[df_m['EQUIPO']==eq].sort_values(col_fecha_m2).iloc[-1]
                    val_s   = ult['SALUD']
                    fecha_v = ult[col_fecha_m2]
                    observ  = ult.get('OBSERVACIONES', ult.get('OBSERVACION',''))
                    color   = "#4CAF50" if val_s>=8 else ("#FFEB3B" if val_s>=6 else "#F44336")
                    desc    = "ÓPTIMO"  if val_s>=8 else ("PREVENTIVO" if val_s>=6 else "CRÍTICO")
                    icono   = "✅" if val_s>=8 else ("⚠️" if val_s>=6 else "🚨")
                    barra_w = int(val_s*10)
                    with cols_eq[i % 3]:
                        st.markdown(f"""
                        <div class="card-equipo" style="border-left:10px solid {color};">
                            <h4 style="margin:0;color:white;">{icono} {eq}</h4>
                            <p style="color:{color};font-weight:bold;margin:4px 0 8px 0;font-size:12px;">{desc}</p>
                            <h2 style="margin:0 0 8px 0;color:{color};">📈 {val_s}/10</h2>
                            <div style="background:#333;border-radius:6px;height:8px;width:100%;">
                                <div style="background:{color};border-radius:6px;height:8px;width:{barra_w}%;"></div>
                            </div>
                            <small style="color:#888;display:block;margin-top:8px;">Última revisión: {fecha_v}</small>
                            {"<small style='color:#AAA;'>"+str(observ)[:80]+"…</small>" if pd.notna(observ) and str(observ).strip() else ""}
                        </div>""", unsafe_allow_html=True)

            st.markdown("---")
            col_v1, col_v2 = st.columns([2,1])
            with col_v1:
                st.write("**🌡️ Mapa de Salud por Equipo y Fecha**")
                if 'EQUIPO' in df_m.columns and 'SALUD' in df_m.columns:
                    df_pivot = df_m.pivot_table(index='EQUIPO', columns=col_fecha_m2,
                                                values='SALUD', aggfunc='last').fillna(0)
                    df_pivot.columns = [str(c) for c in df_pivot.columns]
                    fig_heat = px.imshow(df_pivot,
                                         labels=dict(x="Fecha",y="Equipo",color="Salud"),
                                         color_continuous_scale=['#F44336','#FFEB3B','#4CAF50'],
                                         zmin=0, zmax=10, aspect="auto",
                                         template="plotly_dark", text_auto=True)
                    fig_heat.update_layout(margin=dict(l=10,r=10,t=10,b=10),
                                           height=300, paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_heat, use_container_width=True)

            with col_v2:
                st.write("**📢 Alertas de Mantenimiento**")
                if 'EQUIPO' in df_m.columns and 'SALUD' in df_m.columns:
                    pendientes = (df_m[df_m['SALUD']<7]
                                  .sort_values(col_fecha_m2, ascending=False)
                                  .drop_duplicates('EQUIPO'))
                    if not pendientes.empty:
                        for _, row in pendientes.iterrows():
                            nivel = "🚨 CRÍTICO" if row['SALUD']<6 else "⚠️ PREVENTIVO"
                            st.warning(f"**{row['EQUIPO']}** — {nivel}\n\nSalud: {row['SALUD']}/10")
                    else:
                        st.success("✅ Todos los equipos operan en rangos seguros.")

            if 'EQUIPO' in df_m.columns and 'SALUD' in df_m.columns:
                st.markdown("---")
                st.write("**📈 Evolución de Salud por Equipo**")
                fig_evo = px.line(df_m.sort_values(col_fecha_m2),
                                  x=col_fecha_m2, y='SALUD', color='EQUIPO',
                                  markers=True, template="plotly_dark",
                                  color_discrete_sequence=['#4CAF50','#FFA726','#29B6F6',
                                                           '#CE93D8','#F44336','#FFD54F'])
                fig_evo.add_hrect(y0=0, y1=6, fillcolor="rgba(244,67,54,0.07)",
                                  line_width=0, annotation_text="Zona crítica")
                fig_evo.add_hrect(y0=6, y1=8, fillcolor="rgba(255,235,59,0.07)",
                                  line_width=0, annotation_text="Zona preventiva")
                fig_evo.update_layout(**LAYOUT_BASE, height=350,
                                      yaxis=dict(range=[0,10.5]),
                                      xaxis_title="Fecha", yaxis_title="Salud (0–10)")
                st.plotly_chart(fig_evo, use_container_width=True)

            with st.expander("📝 Ver historial completo de intervenciones"):
                cols_ok = [c for c in df_m.columns if c not in ['MARCA TEMPORAL']]
                st.dataframe(df_m[cols_ok].sort_values(col_fecha_m2, ascending=False),
                             use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ No se cargaron datos de mantenimiento.")

    # ══════════════════════════════════════════
    # TAB 4 — QUÍMICOS
    # ══════════════════════════════════════════
    with t4:
        st.subheader("📦 Gestión de Inventarios y Consumo - Kenzo Jeans")
        STOCK_INICIAL = {"SULFATO DE ALUMINIO":119, "CAL":79, "POLIMERO":24.118}

        if not df_kardex.empty:
            df_k = df_kardex.copy()
            df_k['CANTIDAD'] = pd.to_numeric(
                df_k['CANTIDAD'].astype(str)
                .str.replace(',','.',regex=False)
                .str.replace(r'[^0-9.]','',regex=True),
                errors='coerce').fillna(0)
            df_k['FECHA'] = pd.to_datetime(
                df_k['FECHA'], dayfirst=True, errors='coerce').dt.date

            df_k_periodo = df_k.copy()
            if isinstance(rango,(list,tuple)) and len(rango)==2:
                inicio, fin = rango
                df_k_periodo = df_k_periodo[
                    (df_k_periodo['FECHA']>=inicio) & (df_k_periodo['FECHA']<=fin)]
            if filtro_q:
                df_k_periodo = df_k_periodo[
                    df_k_periodo['NOMBRE DEL QUIMICO'].astype(str)
                    .str.contains(filtro_q, case=False, na=False)]

            df_k['NETO'] = df_k.apply(
                lambda x: x['CANTIDAD']
                if str(x.get('QUE PROCESO VA A REALIZAR','')).upper()=='ENTRADA'
                else -x['CANTIDAD'], axis=1)
            resumen_inv = df_k.groupby('NOMBRE DEL QUIMICO')['NETO'].sum().to_dict()

            st.markdown("#### 📦 Stock Actual")
            ck1,ck2,ck3 = st.columns(3)
            cols_k = [ck1,ck2,ck3]
            for i,(prod,stock_ini) in enumerate(STOCK_INICIAL.items()):
                actual = stock_ini + resumen_inv.get(prod,0)
                alerta = "⚠️ REABASTECER" if actual<20 else "✅ STOCK OK"
                cols_k[i].metric(prod, f"{actual:.1f} kg", delta=alerta,
                                 delta_color="inverse" if actual<20 else "normal")

            st.markdown("**Nivel de stock relativo:**")
            col_bars = st.columns(3)
            for i,(prod,stock_ini) in enumerate(STOCK_INICIAL.items()):
                actual  = stock_ini + resumen_inv.get(prod,0)
                pct     = min(100, max(0, actual/stock_ini*100))
                color_s = "#4CAF50" if pct>40 else ("#FFEB3B" if pct>20 else "#F44336")
                with col_bars[i]:
                    st.markdown(f"""
                    <div style="background:#1E1E2E;border-radius:8px;padding:8px;">
                        <small style="color:#AAA;">{prod[:20]}</small><br>
                        <div style="background:#333;border-radius:4px;height:10px;margin-top:4px;">
                            <div style="background:{color_s};border-radius:4px;height:10px;width:{pct:.0f}%;"></div>
                        </div>
                        <small style="color:{color_s};">{pct:.0f}% del stock inicial</small>
                    </div>""", unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("#### 📊 Consumo en el Periodo Seleccionado")
            df_salidas_p = df_k_periodo[
                df_k_periodo['QUE PROCESO VA A REALIZAR'].astype(str).str.upper()=='SALIDA']
            consumo_periodo = df_salidas_p.groupby('NOMBRE DEL QUIMICO')['CANTIDAD'].sum().to_dict()

            cs1,cs2,cs3 = st.columns(3)
            quimicos_obj = ["SULFATO DE ALUMINIO","CAL","POLIMERO"]
            cols_sal = [cs1,cs2,cs3]
            for i,q in enumerate(quimicos_obj):
                total_sal = consumo_periodo.get(q,0.0)
                n_reg_q   = len(df_salidas_p[df_salidas_p['NOMBRE DEL QUIMICO']==q])
                cols_sal[i].metric(label=f"Salidas: {q}", value=f"{total_sal:.2f} kg",
                                   delta=f"{n_reg_q} registros", delta_color="normal")

            st.markdown("---")
            col_dona, col_tend = st.columns([1,1.5])
            with col_dona:
                st.write("**🍩 Distribución de Consumo Total**")
                df_salidas_all = df_k[df_k['QUE PROCESO VA A REALIZAR'].astype(str).str.upper()=='SALIDA']
                consumo_total  = df_salidas_all.groupby('NOMBRE DEL QUIMICO')['CANTIDAD'].sum().reset_index()
                fig_dona = px.pie(consumo_total, values='CANTIDAD', names='NOMBRE DEL QUIMICO',
                                  hole=0.6, color_discrete_sequence=['#2E7D32','#FBC02D','#1565C0'],
                                  template="plotly_dark")
                fig_dona.update_traces(textinfo='label+percent+value',
                                       texttemplate='%{label}<br>%{percent}<br>%{value:.1f} kg')
                fig_dona.update_layout(**LAYOUT_BASE, height=320)
                st.plotly_chart(fig_dona, use_container_width=True)

            with col_tend:
                st.write("**📈 Consumo Acumulado en el Tiempo**")
                df_sal_t = df_k_periodo[
                    df_k_periodo['QUE PROCESO VA A REALIZAR'].astype(str).str.upper()=='SALIDA'
                ].dropna(subset=['FECHA'])
                if not df_sal_t.empty:
                    df_sal_t = df_sal_t.sort_values('FECHA')
                    df_sal_t['ACUMULADO'] = df_sal_t.groupby('NOMBRE DEL QUIMICO')['CANTIDAD'].cumsum()
                    fig_tend = px.line(df_sal_t, x='FECHA', y='ACUMULADO',
                                       color='NOMBRE DEL QUIMICO', markers=True,
                                       template="plotly_dark",
                                       color_discrete_sequence=['#4CAF50','#FBC02D','#29B6F6'],
                                       labels={'ACUMULADO':'Consumo Acumulado (kg)','FECHA':'Fecha'})
                    fig_tend.update_layout(**LAYOUT_BASE, height=320)
                    st.plotly_chart(fig_tend, use_container_width=True)
                else:
                    st.info("Sin registros de salida en el periodo.")

            st.markdown("---")
            st.write("**🔮 Proyección de Agotamiento de Stock**")
            proj_cols = st.columns(3)
            for i,(prod,stock_ini) in enumerate(STOCK_INICIAL.items()):
                actual      = stock_ini + resumen_inv.get(prod,0)
                df_sal_prod = df_k[
                    (df_k['NOMBRE DEL QUIMICO']==prod) &
                    (df_k['QUE PROCESO VA A REALIZAR'].astype(str).str.upper()=='SALIDA')
                ].dropna(subset=['FECHA'])
                with proj_cols[i]:
                    if not df_sal_prod.empty and len(df_sal_prod)>=2:
                        consumo_d  = df_sal_prod['CANTIDAD'].sum()
                        primer_dia = df_sal_prod['FECHA'].min()
                        ultimo_dia = df_sal_prod['FECHA'].max()
                        dias_rango = max(1,(ultimo_dia-primer_dia).days)
                        tasa       = consumo_d/dias_rango
                        if tasa > 0:
                            dias_rest = int(actual/tasa)
                            color_p   = "#4CAF50" if dias_rest>30 else \
                                        ("#FFEB3B" if dias_rest>10 else "#F44336")
                            st.markdown(f"""
                            <div style="background:#1E1E2E;border-radius:12px;padding:16px;
                                        border-left:6px solid {color_p};">
                                <small style="color:#AAA;">{prod}</small><br>
                                <b style="color:{color_p};font-size:1.4rem;">{dias_rest} días</b><br>
                                <small style="color:#888;">stock restante estimado</small><br>
                                <small style="color:#AAA;">Tasa: {tasa:.2f} kg/día</small>
                            </div>""", unsafe_allow_html=True)
                        else:
                            st.info(f"{prod}: sin consumo detectado.")
                    else:
                        st.info(f"{prod}: insuficientes datos para proyectar.")

            st.markdown("---")
            with st.expander("📋 Historial detallado de movimientos"):
                cols_vista = [c for c in ['FECHA','NOMBRE DEL QUIMICO',
                                           'QUE PROCESO VA A REALIZAR','CANTIDAD']
                              if c in df_k_periodo.columns]
                st.dataframe(df_k_periodo[cols_vista].sort_values('FECHA', ascending=False),
                             column_config={
                                 "CANTIDAD": st.column_config.NumberColumn("Cantidad (kg)", format="%.2f"),
                                 "QUE PROCESO VA A REALIZAR": st.column_config.TextColumn("Tipo Movimiento")
                             }, use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ No se detectaron datos en la hoja de Químicos.")

except Exception as e:
    st.error(f"❌ Error general en la aplicación: {e}")
    st.exception(e)
