import os
import io
import json
import smtplib
import tempfile
import numpy as np
import pandas as pd
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from fpdf import FPDF

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
CORREO_ORIGEN  = "anlambiental@kenzojeans.com.co"
CORREOS_DESTINO = [
    "ambientalkenzo@gmail.com",
    "sgalvis@kenzojeans.com.co",
]

SPREADSHEET_ID = "12iJMb1ujmfzng1NQ7o4iD2COwvkMvxwOrU7s92UT4Ek"

# Nombres exactos de las pestanas en Google Sheets
HOJA_VERT    = "vertimiento"
HOJA_TRATADA = "agua tratada"
HOJA_MANTO   = "mantenimiento"
HOJA_KARDEX  = "kardex"

STOCK_INICIAL = {
    "SULFATO DE ALUMINIO": 119,
    "CAL": 79,
    "POLIMERO": 24.118,
}


# ─────────────────────────────────────────────
# CONEXION A GOOGLE SHEETS
# ─────────────────────────────────────────────
def conectar_sheets():
    """Conecta a Google Sheets usando la cuenta de servicio."""
    creds_json = os.environ.get("GSHEETS_CREDENTIALS", "")
    if not creds_json:
        raise ValueError("GSHEETS_CREDENTIALS no configurado en GitHub Secrets")

    creds_dict = json.loads(creds_json)
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID)


def leer_hoja(spreadsheet, nombre_hoja):
    """Lee una hoja y retorna un DataFrame limpio."""
    try:
        ws = spreadsheet.worksheet(nombre_hoja)
        data = ws.get_all_records()
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)
    except Exception as e:
        print(f"  Advertencia: no se pudo leer '{nombre_hoja}': {e}")
        return pd.DataFrame()


# ─────────────────────────────────────────────
# LIMPIEZA DE DATOS
# ─────────────────────────────────────────────
def limpiar_vertimientos(df):
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    df.columns = df.columns.str.strip()
    mapeo = {
        'pH': 'ph', 'ph': 'ph', 'PH': 'ph',
        'Temperatura': 'temp', 'temp': 'temp',
        'SST': 'sst', 'Solidos suspendidos': 'sst',
        'Fecha': 'fecha', 'fecha': 'fecha', 'Fecha del reporte': 'fecha',
        'Proceso a reportar': 'proceso',
    }
    nuevos = {}
    for col in df.columns:
        if col in mapeo and mapeo[col] not in nuevos.values():
            nuevos[col] = mapeo[col]
    df = df.rename(columns=nuevos)
    for col in ['ph', 'temp', 'sst']:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(',', '.', regex=False),
                errors='coerce').fillna(0)
        else:
            df[col] = 0.0
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], dayfirst=True, errors='coerce').dt.date
    return df.dropna(how='all')


def limpiar_tratada(df):
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    df.columns = df.columns.str.strip()
    mapeo = {
        'pH Tratada': 'ph', 'Temperatura Tratada': 'temp',
        'SST Tratada': 'sst', 'Conductividad Tratada': 'cond',
        'Caudal tratado': 'caudal', 'Fecha': 'fecha',
    }
    nuevos = {}
    for col in df.columns:
        if col in mapeo and mapeo[col] not in nuevos.values():
            nuevos[col] = mapeo[col]
    df = df.rename(columns=nuevos)
    for col in ['ph', 'temp', 'sst', 'cond', 'caudal']:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(',', '.', regex=False),
                errors='coerce').fillna(0)
        else:
            df[col] = 0.0
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], dayfirst=True, errors='coerce').dt.date
    return df.dropna(how='all')


# ─────────────────────────────────────────────
# SANITIZADOR PDF
# ─────────────────────────────────────────────
def _s(txt):
    """Convierte texto a latin-1 seguro para Helvetica."""
    if not isinstance(txt, str):
        txt = str(txt)
    for k, v in {
        '\u2013': '-', '\u2014': '-', '\u2192': '->',
        '\u00b0': 'deg', '\u00e1': 'a', '\u00e9': 'e',
        '\u00ed': 'i', '\u00f3': 'o', '\u00fa': 'u',
        '\u00f1': 'n', '\u00c1': 'A', '\u00c9': 'E',
        '\u00cd': 'I', '\u00d3': 'O', '\u00da': 'U',
        '\u00d1': 'N', '\u00fc': 'u', '\u00e4': 'a',
    }.items():
        txt = txt.replace(k, v)
    return txt.encode('latin-1', errors='replace').decode('latin-1')


# ─────────────────────────────────────────────
# GENERACIÓN DEL PDF
# ─────────────────────────────────────────────
class ReportePDF(FPDF):
    def header(self):
        self.set_fill_color(30, 30, 46)
        self.rect(0, 0, 210, 35, 'F')
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(255, 255, 255)
        self.set_y(10)
        self.cell(0, 8, txt=_s("KENZO JEANS SAS - GESTION AMBIENTAL"), ln=True, align="C")
        self.set_font("Helvetica", "", 10)
        self.cell(0, 6, txt=_s("Reporte Mensual PTAR - Generado automaticamente"), ln=True, align="C")
        self.ln(12)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10,
                  txt=_s(f"Pagina {self.page_no()}/{{nb}} - SGA Kenzo Jeans SAS"),
                  align="C")


def _tabla_header(pdf, cols):
    """Dibuja fila de encabezado de tabla."""
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(46, 46, 78)
    pdf.set_text_color(255, 255, 255)
    for texto, ancho in cols:
        pdf.cell(ancho, 6, txt=_s(texto), border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(0, 0, 0)


def _fila(pdf, valores_anchos, i):
    """Dibuja una fila de datos con zebra striping."""
    fill = (i % 2 == 0)
    pdf.set_fill_color(240, 242, 246)
    for txt_, ancho in valores_anchos:
        pdf.cell(ancho, 5, txt=_s(str(txt_)), border=1, fill=fill, align="C")
    pdf.ln()


def generar_pdf(df_v, df_t, df_m, df_k, periodo_inicio, periodo_fin):
    hoy = datetime.now().strftime('%d/%m/%Y %H:%M')
    f_ini = periodo_inicio.strftime('%d/%m/%Y')
    f_fin = periodo_fin.strftime('%d/%m/%Y')

    pdf = ReportePDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)

    # ── PÁGINA 1: VERTIMIENTOS ──────────────────
    pdf.add_page()
    pdf.set_y(40)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(46, 46, 78)
    pdf.cell(0, 8, txt=_s("1. Vertimientos - Parametros Fisicoquimicos"), ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(3)

    pdf.set_font("Helvetica", "", 9); pdf.set_text_color(50, 50, 50)
    pdf.cell(100, 6, txt=_s(f"Periodo: {f_ini} al {f_fin}"), ln=False)
    pdf.cell(0, 6, txt=_s(f"Emision: {hoy}"), ln=True, align="R")
    pdf.ln(4)

    avg_ph   = df_v['ph'].replace(0, float('nan')).mean()   if not df_v.empty else 0
    avg_temp = df_v['temp'].replace(0, float('nan')).mean() if not df_v.empty else 0
    avg_sst  = df_v['sst'].replace(0, float('nan')).mean()  if not df_v.empty else 0

    _tabla_header(pdf, [("Indicador",50),("Valor Prom.",40),("Estado",45),("Limite",55)])
    for i, (m, v, e, l) in enumerate([
        ("pH Vertimientos", f"{avg_ph:.2f}" if avg_ph else "-",
         "CUMPLE" if avg_ph and 6<=avg_ph<=9 else "ALERTA", "6.0 - 9.0"),
        ("Temperatura", f"{avg_temp:.1f} C" if avg_temp else "-",
         "CUMPLE" if avg_temp and avg_temp<=40 else "ALERTA", "Max 40.0 C"),
        ("SST Entrada", f"{avg_sst:.1f} mg/L" if avg_sst else "-",
         f"Registros: {len(df_v)}", "Control Interno"),
    ]):
        _fila(pdf, [(m,50),(v,40),(e,45),(l,55)], i)
    pdf.ln(5)

    # Grafica pH con matplotlib
    try:
        import matplotlib; matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        df_graf = df_v.dropna(subset=['fecha','ph']).sort_values('fecha')
        df_graf = df_graf[df_graf['ph']>0]
        if not df_graf.empty:
            buf = io.BytesIO()
            fig, ax = plt.subplots(figsize=(10, 3.5))
            ax.plot(df_graf['fecha'], df_graf['ph'],
                    color='#1f77b4', marker='o', linewidth=2, markersize=4, label='pH')
            ax.axhline(y=6, color='red', linestyle='--', alpha=0.7, label='Min (6)')
            ax.axhline(y=9, color='red', linestyle='--', alpha=0.7, label='Max (9)')
            ax.axhspan(6, 9, alpha=0.06, color='green')
            ax.set_title('Tendencia de pH - Vertimientos', fontsize=11, fontweight='bold')
            ax.set_xlabel('Fecha', fontsize=9); ax.set_ylabel('pH', fontsize=9)
            ax.legend(fontsize=8); ax.grid(True, linestyle='--', alpha=0.4)
            fig.autofmt_xdate(rotation=25); plt.tight_layout()
            plt.savefig(buf, format='png', bbox_inches='tight', dpi=130)
            plt.close(fig); buf.seek(0)
            tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            tmp.write(buf.read()); tmp.close()
            pdf.image(tmp.name, x=10, w=190); pdf.ln(3)
            os.unlink(tmp.name)
    except Exception as e:
        pdf.set_font("Helvetica","I",8); pdf.set_text_color(150,50,50)
        pdf.cell(0,5,txt=_s(f"(Grafica no disponible: {e})"),ln=True)

    # Tabla registros recientes
    pdf.set_font("Helvetica","B",9); pdf.set_text_color(46,46,78)
    pdf.cell(0,7,txt=_s("Ultimos registros"),ln=True); pdf.ln(1)
    _tabla_header(pdf,[("Fecha",35),("Proceso",55),("pH",25),("Temp C",30),("SST mg/L",35)])
    for i,(_, row) in enumerate(df_v.sort_values('fecha',ascending=False).head(10).iterrows()):
        _fila(pdf,[
            (str(row.get('fecha','-')),35),
            (str(row.get('proceso','General'))[:22],55),
            (f"{row['ph']:.2f}",25),
            (f"{row['temp']:.1f}",30),
            (f"{row['sst']:.1f}",35),
        ], i)

    # ── PÁGINA 2: AGUA TRATADA ──────────────────
    pdf.add_page(); pdf.set_y(40)
    pdf.set_font("Helvetica","B",12); pdf.set_text_color(46,46,78)
    pdf.cell(0,8,txt=_s("2. Monitoreo de Agua Tratada"),ln=True)
    pdf.line(10,pdf.get_y(),200,pdf.get_y()); pdf.ln(3)

    if not df_t.empty:
        avg_ph_t   = df_t['ph'].replace(0,float('nan')).mean()
        avg_temp_t = df_t['temp'].replace(0,float('nan')).mean()
        avg_sst_t  = df_t['sst'].replace(0,float('nan')).mean()
        total_cau  = df_t['caudal'].replace(0,float('nan')).sum()
        remocion   = max(0,(1-avg_sst_t/avg_sst)*100) \
                     if avg_sst and avg_sst>0 and avg_sst_t and avg_sst_t>0 else 0.0

        _tabla_header(pdf,[("Parametro",50),("Valor Salida",45),("Estado",45),("Referencia",50)])
        for i,(m,v,e,l) in enumerate([
            ("pH Salida", f"{avg_ph_t:.2f}" if avg_ph_t else "-",
             "CUMPLE" if avg_ph_t and 6<=avg_ph_t<=9 else "ALERTA", "6.0 - 9.0"),
            ("Temperatura", f"{avg_temp_t:.1f} C" if avg_temp_t else "-",
             "CUMPLE" if avg_temp_t and avg_temp_t<=40 else "ALERTA", "Max 40.0 C"),
            ("SST Salida", f"{avg_sst_t:.1f} mg/L" if avg_sst_t else "0.0 mg/L",
             f"Efic: {remocion:.1f}%", "Control Interno"),
            ("Vol. Tratado", f"{total_cau:.1f} m3" if total_cau else "-",
             "-", "Periodo"),
        ]):
            _fila(pdf,[(m,50),(v,45),(e,45),(l,50)],i)
        pdf.ln(4)

        # Barra eficiencia
        pdf.set_font("Helvetica","B",9); pdf.set_text_color(46,46,78)
        pdf.cell(0,6,txt=_s(f"Eficiencia de remocion SST: {remocion:.1f}%"),ln=True)
        bar_w=170; filled=int(bar_w*min(remocion/100,1.0))
        c_bar=(46,160,86) if remocion>=70 else ((200,150,0) if remocion>=40 else (180,40,40))
        pdf.set_fill_color(*c_bar); pdf.cell(filled,5,txt='',border=0,fill=True)
        pdf.set_fill_color(200,200,200)
        if bar_w-filled>0: pdf.cell(bar_w-filled,5,txt='',border=0,fill=True)
        pdf.ln(6)

        # Tabla agua tratada
        pdf.set_font("Helvetica","B",9); pdf.set_text_color(46,46,78)
        pdf.cell(0,7,txt=_s("Registros de agua tratada"),ln=True); pdf.ln(1)
        _tabla_header(pdf,[("Fecha",35),("pH",25),("Temp C",30),("SST mg/L",30),("Caudal m3",30),("Cond uS/cm",40)])
        for i,(_, row) in enumerate(df_t.sort_values('fecha',ascending=False).iterrows()):
            _fila(pdf,[
                (str(row.get('fecha','-')),35),(f"{row['ph']:.2f}",25),
                (f"{row['temp']:.1f}",30),(f"{row['sst']:.1f}",30),
                (f"{row['caudal']:.1f}",30),(f"{row['cond']:.1f}",40),
            ], i)
    else:
        pdf.set_font("Helvetica","I",9); pdf.set_text_color(120,120,120)
        pdf.cell(0,6,txt=_s("Sin datos de agua tratada en el periodo."),ln=True)

    # ── PÁGINA 3: MANTENIMIENTO ──────────────────
    pdf.add_page(); pdf.set_y(40)
    pdf.set_font("Helvetica","B",12); pdf.set_text_color(46,46,78)
    pdf.cell(0,8,txt=_s("3. Estado de Equipos - Mantenimiento"),ln=True)
    pdf.line(10,pdf.get_y(),200,pdf.get_y()); pdf.ln(3)

    if not df_m.empty:
        df_mp = df_m.copy()
        df_mp.columns = df_mp.columns.str.strip().str.upper()
        if 'SALUD' in df_mp.columns:
            df_mp['SALUD'] = pd.to_numeric(df_mp['SALUD'],errors='coerce').fillna(0)
        if 'EQUIPO' in df_mp.columns and 'SALUD' in df_mp.columns:
            res_eq = df_mp.groupby('EQUIPO')['SALUD'].last().reset_index()
            n_ok   = int((res_eq['SALUD']>=8).sum())
            n_prev = int(((res_eq['SALUD']>=6)&(res_eq['SALUD']<8)).sum())
            n_crit = int((res_eq['SALUD']<6).sum())
            prom_s = res_eq['SALUD'].mean()

            # KPI resumen
            _tabla_header(pdf,[("Optimos",48),("Preventivos",48),("Criticos",48),("Salud Prom.",46)])
            pdf.set_font("Helvetica","B",12)
            for v,fc in [(str(n_ok),(230,245,230)),(str(n_prev),(255,248,220)),
                         (str(n_crit),(255,230,230)),(f"{prom_s:.1f}/10",(230,240,255))]:
                pdf.set_fill_color(*fc)
                pdf.cell(48,10,txt=_s(v),border=1,fill=True,align="C")
            pdf.ln(14)

            # Tabla equipos
            pdf.set_font("Helvetica","B",9); pdf.set_text_color(46,46,78)
            pdf.cell(0,6,txt=_s("Detalle por equipo"),ln=True); pdf.ln(1)
            col_f=next((c for c in df_mp.columns if 'FECHA' in c),df_mp.columns[0])
            _tabla_header(pdf,[("Equipo",65),("Salud",25),("Estado",40),("Ult. Revision",60)])
            for i, row in res_eq.sort_values('SALUD').iterrows():
                s   = row['SALUD']
                est = "OPTIMO" if s>=8 else ("PREVENTIVO" if s>=6 else "CRITICO")
                ult = df_mp[df_mp['EQUIPO']==row['EQUIPO']][col_f].iloc[-1] \
                      if col_f in df_mp.columns else "-"
                fill=i%2==0; pdf.set_fill_color(240,242,246)
                c_e=(46,160,86) if s>=8 else ((200,130,0) if s>=6 else (180,40,40))
                pdf.set_font("Helvetica","",8); pdf.set_text_color(0,0,0)
                pdf.cell(65,6,txt=_s(str(row['EQUIPO'])),border=1,fill=fill)
                pdf.cell(25,6,txt=_s(f"{s:.0f}/10"),border=1,fill=fill,align="C")
                pdf.set_text_color(*c_e)
                pdf.cell(40,6,txt=_s(est),border=1,fill=fill,align="C")
                pdf.set_text_color(0,0,0)
                pdf.cell(60,6,txt=_s(str(ult)),border=1,fill=fill,align="C")
                pdf.ln()
    else:
        pdf.set_font("Helvetica","I",9); pdf.set_text_color(120,120,120)
        pdf.cell(0,6,txt=_s("Sin datos de mantenimiento en el periodo."),ln=True)

    # ── PÁGINA 4: QUÍMICOS ──────────────────────
    pdf.add_page(); pdf.set_y(40)
    pdf.set_font("Helvetica","B",12); pdf.set_text_color(46,46,78)
    pdf.cell(0,8,txt=_s("4. Inventario y Consumo de Quimicos"),ln=True)
    pdf.line(10,pdf.get_y(),200,pdf.get_y()); pdf.ln(3)

    if not df_k.empty:
        df_kp = df_k.copy()
        df_kp.columns = df_kp.columns.str.strip().str.upper()
        if 'CANTIDAD' in df_kp.columns:
            df_kp['CANTIDAD']=pd.to_numeric(
                df_kp['CANTIDAD'].astype(str).str.replace(',','.',regex=False)
                .str.replace(r'[^0-9.]','',regex=True),errors='coerce').fillna(0)
        proc_col=next((c for c in df_kp.columns if 'PROCESO' in c or 'TIPO' in c),None)
        nom_col =next((c for c in df_kp.columns if 'QUIMICO' in c or 'NOMBRE' in c),None)

        if proc_col and nom_col:
            df_kp['NETO']=df_kp.apply(
                lambda x: x['CANTIDAD'] if str(x[proc_col]).upper()=='ENTRADA'
                else -x['CANTIDAD'], axis=1)
            res_inv=df_kp.groupby(nom_col)['NETO'].sum().to_dict()
            df_sal =df_kp[df_kp[proc_col].astype(str).str.upper()=='SALIDA']
            cons_t =df_sal.groupby(nom_col)['CANTIDAD'].sum().to_dict()

            # Tabla stock
            _tabla_header(pdf,[("Quimico",58),("Stock Ini.",32),("Consumo",32),
                                ("Stock Act.",32),("% Stock",22),("Estado",24)])
            for i,(prod,ini) in enumerate(STOCK_INICIAL.items()):
                actual=ini+res_inv.get(prod,0)
                consumo=cons_t.get(prod,0)
                pct=min(100,max(0,actual/ini*100))
                estado="OK" if actual>=20 else "REAB."
                _fila(pdf,[
                    (prod,58),(f"{ini:.0f}kg",32),(f"{consumo:.1f}kg",32),
                    (f"{actual:.1f}kg",32),(f"{pct:.0f}%",22),(estado,24)
                ], i)
            pdf.ln(5)

            # Barras de nivel
            pdf.set_font("Helvetica","B",9); pdf.set_text_color(46,46,78)
            pdf.cell(0,6,txt=_s("Nivel de stock:"),ln=True); pdf.ln(2)
            for prod,ini in STOCK_INICIAL.items():
                actual=ini+res_inv.get(prod,0)
                pct=min(1.0,max(0.0,actual/ini))
                c_bar=(46,160,86) if pct>0.4 else ((200,150,0) if pct>0.2 else (180,40,40))
                bar_w=110; filled=int(bar_w*pct)
                pdf.set_font("Helvetica","",8); pdf.set_text_color(0,0,0)
                pdf.cell(62,5,txt=_s(prod),border=0)
                pdf.set_fill_color(*c_bar); pdf.cell(filled,5,txt='',border=0,fill=True)
                pdf.set_fill_color(200,200,200)
                if bar_w-filled>0: pdf.cell(bar_w-filled,5,txt='',border=0,fill=True)
                pdf.set_text_color(*c_bar)
                pdf.cell(0,5,txt=_s(f"  {pct*100:.0f}% ({actual:.1f} kg)"),ln=True)
                pdf.set_text_color(0,0,0)
            pdf.ln(4)

            # Proyeccion
            pdf.set_font("Helvetica","B",9); pdf.set_text_color(46,46,78)
            pdf.cell(0,6,txt=_s("Proyeccion de agotamiento:"),ln=True); pdf.ln(1)
            _tabla_header(pdf,[("Quimico",65),("Stock Actual",40),("Tasa kg/dia",40),("Dias restantes",45)])
            if 'FECHA' in df_kp.columns:
                df_kp['FECHA']=pd.to_datetime(df_kp['FECHA'],dayfirst=True,errors='coerce').dt.date
            for i,(prod,ini) in enumerate(STOCK_INICIAL.items()):
                actual=ini+res_inv.get(prod,0)
                df_sp=df_kp[(df_kp[nom_col]==prod)&
                            (df_kp[proc_col].astype(str).str.upper()=='SALIDA')]
                if 'FECHA' in df_sp.columns:
                    df_sp=df_sp.dropna(subset=['FECHA'])
                if not df_sp.empty and len(df_sp)>=2:
                    d1,d2=df_sp['FECHA'].min(),df_sp['FECHA'].max()
                    dias=max(1,(d2-d1).days)
                    tasa=df_sp['CANTIDAD'].sum()/dias
                    dias_r=int(actual/tasa) if tasa>0 else 9999
                    _fila(pdf,[(prod,65),(f"{actual:.1f}kg",40),(f"{tasa:.2f}",40),(f"{dias_r} dias",45)],i)
                else:
                    _fila(pdf,[(prod,65),(f"{actual:.1f}kg",40),("Sin datos",40),("-",45)],i)
    else:
        pdf.set_font("Helvetica","I",9); pdf.set_text_color(120,120,120)
        pdf.cell(0,6,txt=_s("Sin datos de quimicos."),ln=True)

    # ── DECLARACIÓN ─────────────────────────────
    pdf.ln(8)
    pdf.set_font("Helvetica","B",9); pdf.set_text_color(46,46,78)
    pdf.cell(0,7,txt=_s("Declaracion de Conformidad"),ln=True)
    pdf.line(10,pdf.get_y(),200,pdf.get_y()); pdf.ln(3)
    pdf.set_font("Helvetica","",8); pdf.set_text_color(60,60,60)
    pdf.multi_cell(0,5,txt=_s(
        "El presente reporte fue generado automaticamente por el Sistema de Gestion "
        "Ambiental (SGA) de Kenzo Jeans SAS. Los datos corresponden al periodo indicado "
        "y tienen caracter informativo de seguimiento ambiental interno."))
    pdf.ln(8)
    pdf.set_draw_color(46,46,78)
    pdf.line(20,pdf.get_y(),90,pdf.get_y())
    pdf.line(120,pdf.get_y(),190,pdf.get_y()); pdf.ln(2)
    pdf.set_font("Helvetica","",8); pdf.set_text_color(80,80,80)
    pdf.cell(95,5,txt=_s("Responsable PTAR - Kenzo Jeans SAS"),align="C")
    pdf.cell(95,5,txt=_s("Director Ambiental - Kenzo Jeans SAS"),align="C")

    return pdf.output(dest='S').encode('latin-1')


# ─────────────────────────────────────────────
# ENVÍO POR CORREO (OUTLOOK SMTP)
# ─────────────────────────────────────────────
def enviar_correo(pdf_bytes, periodo_inicio, periodo_fin):
    outlook_user = os.environ.get("OUTLOOK_USER", "")
    outlook_pass = os.environ.get("OUTLOOK_PASS", "")

    if not outlook_user or not outlook_pass:
        raise ValueError("OUTLOOK_USER o OUTLOOK_PASS no configurados en GitHub Secrets")

    mes_nombre = periodo_fin.strftime('%B %Y')
    nombre_archivo = f"Reporte_PTAR_Kenzo_{periodo_fin.strftime('%Y%m')}.pdf"

    msg = MIMEMultipart()
    msg['From']    = outlook_user
    msg['To']      = ", ".join(CORREOS_DESTINO)
    msg['Subject'] = f"Reporte Mensual PTAR - Kenzo Jeans SAS - {mes_nombre}"

    cuerpo = f"""Estimado equipo,

Adjunto encontraran el Reporte Mensual de la Planta de Tratamiento de Aguas Residuales (PTAR)
correspondiente al periodo {periodo_inicio.strftime('%d/%m/%Y')} - {periodo_fin.strftime('%d/%m/%Y')}.

El informe incluye:
  - Parametros fisicoquimicos de vertimientos (pH, temperatura, SST)
  - Monitoreo de agua tratada y eficiencia de remocion
  - Estado de equipos y mantenimiento
  - Inventario y consumo de quimicos con proyeccion de agotamiento

Este correo fue generado automaticamente por el Sistema de Gestion Ambiental (SGA).

Saludos,
Sistema de Gestion Ambiental
Kenzo Jeans SAS
"""
    msg.attach(MIMEText(cuerpo, 'plain', 'utf-8'))

    # Adjuntar PDF
    part = MIMEBase('application', 'pdf')
    part.set_payload(pdf_bytes)
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename="{nombre_archivo}"')
    msg.attach(part)

    # Enviar via Outlook SMTP
    print(f"  Conectando a smtp.office365.com:587...")
    with smtplib.SMTP('smtp.office365.com', 587) as server:
        server.ehlo()
        server.starttls()
        server.login(outlook_user, outlook_pass)
        server.sendmail(outlook_user, CORREOS_DESTINO, msg.as_string())

    print(f"  Correo enviado a: {', '.join(CORREOS_DESTINO)}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    print("=" * 50)
    print("SGA - Reporte Mensual PTAR - Kenzo Jeans")
    print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # Periodo: mes anterior completo
    hoy = date.today()
    if hoy.month == 1:
        periodo_fin   = date(hoy.year - 1, 12, 31)
        periodo_inicio = date(hoy.year - 1, 12, 1)
    else:
        import calendar
        ultimo_dia = calendar.monthrange(hoy.year, hoy.month - 1)[1]
        periodo_inicio = date(hoy.year, hoy.month - 1, 1)
        periodo_fin    = date(hoy.year, hoy.month - 1, ultimo_dia)

    print(f"Periodo del reporte: {periodo_inicio} al {periodo_fin}")

    # 1. Conectar y leer datos
    print("\n[1/3] Leyendo datos de Google Sheets...")
    try:
        spreadsheet = conectar_sheets()
        df_vert    = limpiar_vertimientos(leer_hoja(spreadsheet, HOJA_VERT))
        df_tratada = limpiar_tratada(leer_hoja(spreadsheet, HOJA_TRATADA))
        df_manto   = leer_hoja(spreadsheet, HOJA_MANTO)
        df_kardex  = leer_hoja(spreadsheet, HOJA_KARDEX)
        if not df_kardex.empty:
            df_kardex.columns = df_kardex.columns.str.strip().str.upper()
        print(f"  Vertimientos:  {len(df_vert)} registros")
        print(f"  Agua tratada:  {len(df_tratada)} registros")
        print(f"  Mantenimiento: {len(df_manto)} registros")
        print(f"  Kardex:        {len(df_kardex)} registros")
    except Exception as e:
        print(f"ERROR leyendo Google Sheets: {e}")
        raise

    # Filtrar por periodo
    def filtrar_periodo(df, col='fecha'):
        if df.empty or col not in df.columns:
            return df
        return df[(df[col] >= periodo_inicio) & (df[col] <= periodo_fin)]

    df_vert    = filtrar_periodo(df_vert)
    df_tratada = filtrar_periodo(df_tratada)

    # 2. Generar PDF
    print("\n[2/3] Generando PDF...")
    try:
        pdf_bytes = generar_pdf(
            df_vert, df_tratada, df_manto, df_kardex,
            periodo_inicio, periodo_fin
        )
        print(f"  PDF generado: {len(pdf_bytes)/1024:.1f} KB")
    except Exception as e:
        print(f"ERROR generando PDF: {e}")
        raise

    # 3. Enviar correo
    print("\n[3/3] Enviando correo...")
    try:
        enviar_correo(pdf_bytes, periodo_inicio, periodo_fin)
    except Exception as e:
        print(f"ERROR enviando correo: {e}")
        raise

    print("\n✓ Reporte enviado exitosamente!")
    print("=" * 50)


if __name__ == "__main__":
    main()
