import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io

st.set_page_config(page_title="Control PTAR", layout="wide")
st.title("💧 Control de Vertimientos (Tiempo Real)")

# --- INSTRUCCIÓN: Copia el link de tu navegador y pégalo aquí abajo ---
# Asegúrate de que incluya desde 'https://' hasta el final
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTYSPFoH-9tDls-EOx6h_4U0GWVcV8ip704Hx5dYkY-l1X4gwKvEHqujuxA_UfvQrB8TKuz4Sy5qQe3/pubhtml"

@st.cache_data(ttl=60)
def cargar_datos_seguro(url):
    try:
        # 1. Limpieza y transformación del link
        base_url = url.split('/edit')[0]
        # Extraemos el GID (ID de la pestaña) si existe, si no usamos 0
        gid = "0"
        if "gid=" in url:
            gid = url.split("gid=")[1].split("&")[0]
        
        csv_url = f"{base_url}/export?format=csv&gid={gid}"
        
        # 2. Intento de descarga
        response = requests.get(csv_url, timeout=10)
        
        # Si Google devuelve una página de login (HTML), es un tema de link o permiso
        if "<!DOCTYPE html>" in response.text:
            st.error("🚨 Google Sheets devolvió una página web en lugar de datos.")
            st.info("Revisa que el link en el código sea el correcto y que el Sheet esté como 'Cualquier persona con el enlace'.")
            st.stop()
            
        # 3. Procesamiento de datos
        df = pd.read_csv(io.StringIO(response.text))
        
        # Limpieza de columnas
        df.columns = [c.strip() for c in df.columns]
        
        # Conversión de números (Puntos y Comas)
        for col in ['ph', 'Temperatura', 'Solidos suspendidos']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
        
        if 'Fecha' in df.columns:
            df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
            
        return df

    except Exception as e:
        st.error(f"No se pudo conectar con el Sheet: {e}")
        st.stop()

# --- EJECUCIÓN ---
if SHEET_URL == "TU_LINK_DE_GOOGLE_SHEETS_AQUÍ":
    st.warning("⚠️ Por favor, pega tu link de Google Sheets en la línea 12 del código en GitHub.")
else:
    df = cargar_datos_seguro(SHEET_URL)
    
    if df is not None:
        st.success("✅ Datos sincronizados correctamente")
        
        # Métricas rápidas
        c1, c2, c3 = st.columns(3)
        if 'ph' in df.columns:
            c1.metric("pH Promedio", f"{df['ph'].mean():.2f}")
        if 'Temperatura' in df.columns:
            c2.metric("Temp. Promedio", f"{df['Temperatura'].mean():.1f} °C")
        if 'Solidos suspendidos' in df.columns:
            c3.metric("Sólidos Promedio", f"{df['Solidos suspendidos'].mean():.1f}")

        # Gráfico dinámico
        st.markdown("### Tendencia de Parámetros")
        opcion = st.selectbox("Elegir parámetro:", ['ph', 'Temperatura', 'Solidos suspendidos'])
        
        fig = px.line(df, x='Fecha', y=opcion, color='Proceso' if 'Proceso' in df.columns else None, 
                     markers=True, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("Ver tabla completa"):
            st.dataframe(df)
