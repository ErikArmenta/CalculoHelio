# -*- coding: utf-8 -*-
"""
Created on Tue Jan 13 07:24:32 2026

@author: acer
"""

import streamlit as st
import pandas as pd
import altair as alt
import os

# --- 1. CONFIGURACIÓN DE PÁGINA PRO ---
st.set_page_config(
    page_title="Helium Recovery System | Erik Armenta",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. SIDEBAR CON LOGO Y SELECTOR DE TIEMPO ---
with st.sidebar:
    logo_path = "EA_2.png"
    if os.path.exists(logo_path):
        st.image(logo_path, use_container_width=True)
    else:
        st.warning("Coloca 'logo.png' en la raíz")

    st.title("Control Panel")
    st.markdown("---")

    # Selector de rango visual
    st.subheader("Visual Range")
    view_option = st.selectbox(
        "Mostrar datos de:",
        ["Últimas 24 Horas", "Últimos 7 Días", "Todo el Historial"]
    )

    st.markdown("---")
    st.write("**Engineer in Charge:**")
    st.info("Erik Armenta")
    st.caption("_Accuracy is our signature, and innovation is our nature._")

# --- 3. CARGA Y LÓGICA ORIGINAL (INTEGRIDAD TOTAL) ---
sheet_id = "11LjeT8pJLituxpCxYKxWAC8ZMFkgtts6sJn3X-F35A4"
csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=430617011"

@st.cache_data(ttl=60)
def load_and_calculate():
    df = pd.read_csv(csv_url)
    df['Marca temporal'] = pd.to_datetime(df['Marca temporal'])
    df = df.sort_values('Marca temporal')

    BASE_VOLUME = 450.00
    df['Temperatura Fahrenheit'] = df['Temperatura Celsius'] * 1.8 + 32
    df['Temperature Over'] = df['Temperatura Fahrenheit']

    # Lógica de Presión: Manométrica + Atmosférica
    df['Vessel Pressure'] = df['Presión'] + 14.7

    # Compressibility Factor (Z)
    t_term = 459.7 + df['Temperature Over']
    part1 = 0.000102297 - (0.000000192998 * t_term) + (0.00000000011836 * (t_term**2))
    df['Compressibility Factor (Z)'] = 1 + (part1 * df['Vessel Pressure']) - (0.0000000002217 * (df['Vessel Pressure']**2))

    # Volume Factor (Fv)
    f_temp = 529.7 / (df['Temperature Over'] + 459.7)
    f_pres = df['Vessel Pressure'] / 14.7
    f_comp = 1.00049 / df['Compressibility Factor (Z)']
    f_exp_metal = 1 + (0.0000189 * (df['Temperature Over'] - 70))
    f_pres_efect = 1 + (0.00000074 * df['Vessel Pressure'])
    df['Volume Factor (Fv)'] = f_temp * f_pres * f_comp * f_exp_metal * f_pres_efect

    # Resultados Finales
    df['Volume Helium ft3'] = (BASE_VOLUME * df['Volume Factor (Fv)'])
    df['Volume in Cubic Meters ( M3 )'] = df['Volume Helium ft3'] / 35.315

    # Consumo (Diferencia vs Anterior)
    df['Diferencia M3'] = df['Volume in Cubic Meters ( M3 )'].diff().fillna(0)
    df['Consumo Absoluto M3'] = df['Diferencia M3'].abs()

    return df

# Procesamos todo el histórico para que el .diff() no falle
df_full = load_and_calculate()

# --- 4. FILTRO PARA VISTA DE USUARIO ---
if view_option == "Últimas 24 Horas":
    cutoff = pd.Timestamp.now() - pd.Timedelta(hours=24)
    df_vista = df_full[df_full['Marca temporal'] >= cutoff].copy()
elif view_option == "Últimos 7 Días":
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=7)
    df_vista = df_full[df_full['Marca temporal'] >= cutoff].copy()
else:
    df_vista = df_full.copy()

# --- 5. INTERFAZ Y MÉTRICAS ---
st.title("🛡️ Helium Recovery System")
st.caption("Industrial Monitoring & Thermodynamic Calculation Engine")

if not df_full.empty:
    last = df_full.iloc[-1]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Volumen M3", f"{last['Volume in Cubic Meters ( M3 )']:.2f}", f"{last['Diferencia M3']:.4f}")
    c2.metric("Presión Absoluta", f"{last['Vessel Pressure']:.1f} PSIA")
    c3.metric("Factor Fv", f"{last['Volume Factor (Fv)']:.4f}")

    alert_color = "inverse" if last['Consumo Absoluto M3'] > 2 else "normal"
    c4.metric("Consumo Neto", f"{last['Consumo Absoluto M3']:.2f} M3",
              "⚠️ ALTA" if last['Consumo Absoluto M3'] > 2 else "OK", delta_color=alert_color)

st.divider()

# --- 6. TABLA Y BOTÓN DE DESCARGA ---
col_table, col_btn = st.columns([0.8, 0.2])
with col_table:
    st.subheader(f"Data Log: {view_option}")
with col_btn:
    # Botón para descargar lo que se está viendo
    csv = df_vista.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Descargar Reporte", data=csv, file_name=f"Helio_Report_{view_option}.csv", mime='text/csv')

st.dataframe(df_vista, use_container_width=True)

# --- 7. GRÁFICA CON HOVER DATA COMPLETO (PRO) ---
st.subheader("Análisis de Tendencia y Alertas de Consumo")
df_vista['Alerta'] = df_vista['Consumo Absoluto M3'] > 2

# Definición del gráfico con todos los campos en el tooltip
chart = alt.Chart(df_vista).mark_line(point=True).encode(
    x=alt.X('Marca temporal:T', title='Marca de Tiempo'),
    y=alt.Y('Volume in Cubic Meters ( M3 ):Q', title='Volumen M3'),
    color=alt.condition(
        alt.datum.Alerta == True,
        alt.value('#FF0000'), # Rojo Brilloso
        alt.value('#5271ff')  # Azul
    ),
    tooltip=[
        alt.Tooltip('Marca temporal:T', title='Fecha y Hora'),
        alt.Tooltip('Temperatura Celsius:Q', title='Temp Celsius (°C)'),
        alt.Tooltip('Temperatura Fahrenheit:Q', title='Temp Fahrenheit (°F)'),
        alt.Tooltip('Presión:Q', title='P. Manométrica (PSI)'),
        alt.Tooltip('Vessel Pressure:Q', title='P. Absoluta (PSIA)'),
        alt.Tooltip('Compressibility Factor (Z):Q', title='Factor Z', format='.5f'),
        alt.Tooltip('Volume Factor (Fv):Q', title='Factor Fv', format='.5f'),
        alt.Tooltip('Volume Helium ft3:Q', title='Volumen (ft³)', format='.2f'),
        alt.Tooltip('Volume in Cubic Meters ( M3 ):Q', title='Total (M³)', format='.2f'),
        alt.Tooltip('Diferencia M3:Q', title='Diferencia Real (M³)', format='.4f'),
        alt.Tooltip('Consumo Absoluto M3:Q', title='Consumo Neto (M³)', format='.4f')
    ]
).interactive().properties(height=450)

st.altair_chart(chart, use_container_width=True)

if df_vista['Alerta'].any():
    st.error("🚨 Alerta: Se detectaron fluctuaciones de consumo superiores a 2 m³ en el rango seleccionado.")

# --- 8. FOOTER FIRMA ---
st.markdown(
    """
    <div style="text-align: center; color: #6d6d6d; font-size: 0.9em; margin-top: 50px;">
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <h3 style="margin-bottom: 5px;">🚀 Monitor de Recuperación de Helio v1.0</h3>
        <p style="margin: 0;"><b>Developed by:</b> Master Engineer Erik Armenta</p>
        <p style="font-style: italic; color: #5271ff; font-weight: 500; margin-top: 5px;">
            "Accuracy is our signature, and innovation is our nature."
        </p>
    </div>
    """,
    unsafe_allow_html=True
)