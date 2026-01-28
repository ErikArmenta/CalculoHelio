# -*- coding: utf-8 -*-
"""
Created on Tue Jan 13 07:24:32 2026

@author: acer
"""

import streamlit as st
import pandas as pd
import altair as alt
import os

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Helium Recovery System | Monitoring",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. SIDEBAR ---
with st.sidebar:
    logo_path = "EA_2.png"
    if os.path.exists(logo_path):
        st.image(logo_path, use_container_width=True)
    else:
        st.warning("Coloca 'EA_2.png' en la raíz")

    st.title("Control Panel")
    st.markdown("---")

    view_option = st.selectbox(
        "Mostrar datos de:",
        ["Últimas 24 Horas", "Últimos 7 Días", "Todo el Historial"]
    )

    if st.button("🔄 Recargar Datos Originales"):
        st.cache_data.clear()
        if 'master_data' in st.session_state:
            del st.session_state['master_data']
        st.rerun()

    st.markdown("---")
    st.write("**Engineer in Charge:**")
    st.info("Erik Armenta")
    st.caption("_Accuracy is our signature, and innovation is our nature._")

# --- 3. LÓGICA TERMODINÁMICA (Mantenida intacta) ---
sheet_id = "11LjeT8pJLituxpCxYKxWAC8ZMFkgtts6sJn3X-F35A4"
csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=430617011"

@st.cache_data(ttl=60)
def fetch_raw_data():
    df = pd.read_csv(csv_url)
    df['Marca temporal'] = pd.to_datetime(df['Marca temporal'])
    df = df.sort_values('Marca temporal').reset_index(drop=True)
    return df

def calculate_thermodynamics(df_input):
    df = df_input.copy()
    df['Marca temporal'] = pd.to_datetime(df['Marca temporal'])
    df = df.sort_values('Marca temporal') # Re-ordenar por si cambió el tiempo

    cols_check = ['Temperatura Celsius', 'Presión']
    for col in cols_check:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df = df.dropna(subset=cols_check)
    BASE_VOLUME = 450.00

    df['Temperatura Fahrenheit'] = df['Temperatura Celsius'] * 1.8 + 32
    df['Temperature Over'] = df['Temperatura Fahrenheit']
    df['Vessel Pressure'] = df['Presión'] + 14.7

    t_term = 459.7 + df['Temperature Over']
    part1 = 0.000102297 - (0.000000192998 * t_term) + (0.00000000011836 * (t_term**2))
    df['Compressibility Factor (Z)'] = 1 + (part1 * df['Vessel Pressure']) - (0.0000000002217 * (df['Vessel Pressure']**2))

    f_temp = 529.7 / (df['Temperature Over'] + 459.7)
    f_pres = df['Vessel Pressure'] / 14.7
    f_comp = 1.00049 / df['Compressibility Factor (Z)']
    f_exp_metal = 1 + (0.0000189 * (df['Temperature Over'] - 70))
    f_pres_efect = 1 + (0.00000074 * df['Vessel Pressure'])
    df['Volume Factor (Fv)'] = f_temp * f_pres * f_comp * f_exp_metal * f_pres_efect

    df['Volume Helium ft3'] = (BASE_VOLUME * df['Volume Factor (Fv)'])
    df['Volume in Cubic Meters ( M3 )'] = df['Volume Helium ft3'] / 35.315

    df['Diferencia M3'] = df['Volume in Cubic Meters ( M3 )'].diff().fillna(0)
    df['Consumo Absoluto M3'] = df['Diferencia M3'].abs()

    return df.reset_index(drop=True)

# --- 4. GESTIÓN DE ESTADO (SESSION STATE) ---
if 'master_data' not in st.session_state:
    try:
        raw_df = fetch_raw_data()
        st.session_state.master_data = calculate_thermodynamics(raw_df)
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        st.stop()

df_full = st.session_state.master_data

# --- 5. FILTRADO ---
if view_option == "Últimas 24 Horas":
    cutoff = pd.Timestamp.now() - pd.Timedelta(hours=24)
    df_vista = df_full[df_full['Marca temporal'] >= cutoff].copy()
elif view_option == "Últimos 7 Días":
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=7)
    df_vista = df_full[df_full['Marca temporal'] >= cutoff].copy()
else:
    df_vista = df_full.copy()

# --- 6. KPI DASHBOARD ---
st.title("🛡️ Helium Recovery System")
st.caption("Industrial Monitoring & Thermodynamic Calculation Engine")

if not df_vista.empty:
    last = df_vista.iloc[-1]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Volumen M3", f"{last['Volume in Cubic Meters ( M3 )']:.2f}", f"{last['Diferencia M3']:.4f}")
    c2.metric("Presión Absoluta", f"{last['Vessel Pressure']:.1f} PSIA")
    c3.metric("Factor Fv", f"{last['Volume Factor (Fv)']:.4f}")

    alert_val = last['Consumo Absoluto M3'] > 5
    c4.metric("Consumo Neto", f"{last['Consumo Absoluto M3']:.2f} M3",
              "⚠️ ALTA" if alert_val else "OK", delta_color="inverse" if alert_val else "normal")

st.divider()

# --- 7. TABLA EDITOR INTERACTIVO ---
col_table, col_btn = st.columns([0.8, 0.2])

with col_table:
    st.subheader(f"Data Log: {view_option}")
    st.info("✍️ **Modo Editor Habilitado:** Corrige la hora de lectura real, temperatura o presión.")

    column_cfg = {
        "Marca temporal": st.column_config.DatetimeColumn("Tiempo (Editable)", format="D MMM YYYY, H:mm", required=True),
        "Temperatura Celsius": st.column_config.NumberColumn("Temp (°C)", format="%.2f", step=0.1),
        "Presión": st.column_config.NumberColumn("Presión (PSI)", format="%.2f", step=0.1),
        "Volume in Cubic Meters ( M3 )": st.column_config.NumberColumn("Volumen (M³)", format="%.4f", disabled=True),
        "Consumo Absoluto M3": st.column_config.NumberColumn("Consumo (M³)", format="%.4f", disabled=True),
    }

    edited_df = st.data_editor(
        df_vista,
        column_config=column_cfg,
        use_container_width=True,
        key="data_editor",
        num_rows="fixed"
    )

    if not edited_df.equals(df_vista):
        st.session_state.master_data.update(edited_df)
        st.session_state.master_data = calculate_thermodynamics(st.session_state.master_data)
        st.rerun()

with col_btn:
    st.write("")
    st.write("")
    st.write("")
    # BOTÓN DE GUARDADO / DESCARGA
    csv = df_full.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="💾 Guardar y Descargar CSV",
        data=csv,
        file_name=f"Helium_Report_Corregido.csv",
        mime='text/csv',
        help="Descarga el historial completo con las correcciones de tiempo y datos realizadas."
    )

# --- 8. GRÁFICA DINÁMICA CON HOVERS MEJORADOS ---
st.subheader("Análisis de Tendencia")

plot_data = edited_df.copy()
plot_data['Alerta'] = plot_data['Consumo Absoluto M3'] > 5

chart = alt.Chart(plot_data).mark_line(point=True).encode(
    x=alt.X('Marca temporal:T', title='Tiempo'),
    y=alt.Y('Volume in Cubic Meters ( M3 ):Q', title='Volumen M3'),
    color=alt.condition(
        alt.datum.Alerta == True,
        alt.value('#FF0000'), # Rojo para alertas
        alt.value('#5271ff')  # Azul normal
    ),
    tooltip=[
        alt.Tooltip('Marca temporal:T', title='Hora Real', format='%Y-%m-%d %H:%M'),
        alt.Tooltip('Temperatura Celsius:Q', title='Temp C', format='.2f'),
        alt.Tooltip('Presión:Q', title='Presión PSI', format='.2f'),
        alt.Tooltip('Volume in Cubic Meters ( M3 ):Q', title='Volumen M3', format='.4f'),
        alt.Tooltip('Consumo Absoluto M3:Q', title='Consumo Absoluto M3', format='.4f') # HOVER SOLICITADO
    ]
).interactive().properties(height=450)

st.altair_chart(chart, use_container_width=True)

if plot_data['Alerta'].any():
    st.error("🚨 Alerta: Se detectaron fluctuaciones de consumo superiores a 5 m³ en el rango seleccionado.")



# --- 9. NUEVA GRÁFICA MULTI-VARIABLE ---
st.subheader("Correlación de Variables (PSI, Volumen, Temp °F)")

# Derretimos el dataframe para que Altair pueda manejar múltiples colores por variable
df_melted = plot_data.melt(
    id_vars=['Marca temporal'],
    value_vars=['Presión', 'Volume in Cubic Meters ( M3 )', 'Temperatura Fahrenheit'],
    var_name='Variable',
    value_name='Valor'
)

# Diccionario de colores solicitado
color_scale = alt.Scale(
    domain=['Presión', 'Volume in Cubic Meters ( M3 )', 'Temperatura Fahrenheit'],
    range=['#FF0000', '#0000FF', '#FFD700'] # Rojo, Azul, Dorado/Amarillo
)

multi_chart = alt.Chart(df_melted).mark_line(point=True).encode(
    x=alt.X('Marca temporal:T', title='Tiempo'),
    y=alt.Y('Valor:Q', title='Escala Unificada', scale=alt.Scale(zero=False)),
    color=alt.Color('Variable:N', scale=color_scale, title="Leyenda"),
    tooltip=['Marca temporal:T', 'Variable:N', 'Valor:Q']
).interactive().properties(height=450)

st.altair_chart(multi_chart, use_container_width=True)


# --- 9. FIRMA ---
st.markdown(
    """
    <div style="text-align: center; color: #6d6d6d; font-size: 0.9em; margin-top: 50px;">
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <h3 style="margin-bottom: 5px;">🚀 Monitor de Recuperación de Helio v1.4</h3>
        <p style="margin: 0;"><b>Developed by:</b> Master Engineer Erik Armenta</p>
        <p style="font-style: italic; color: #5271ff; font-weight: 500; margin-top: 5px;">
            "Accuracy is our signature, and innovation is our nature."
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

