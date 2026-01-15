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

    if st.button("🔄 Recargar Datos Originales"):
        st.cache_data.clear()
        if 'master_data' in st.session_state:
            del st.session_state['master_data']
        st.rerun()

    st.markdown("---")
    st.write("**Engineer in Charge:**")
    st.info("Erik Armenta")
    st.caption("_Accuracy is our signature, and innovation is our nature._")

# --- 3. FUNCIONES ESTRUCTURALES (Separación de Lógica y Datos) ---
sheet_id = "11LjeT8pJLituxpCxYKxWAC8ZMFkgtts6sJn3X-F35A4"
csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=430617011"

@st.cache_data(ttl=60)
def fetch_raw_data():
    """Descarga limpia de datos."""
    df = pd.read_csv(csv_url)
    df['Marca temporal'] = pd.to_datetime(df['Marca temporal'])
    df = df.sort_values('Marca temporal')
    # Reset index to ensure unique sequential index for merging edits
    df = df.reset_index(drop=True)
    return df

def calculate_thermodynamics(df_input):
    """
    Motor de cálculo termodinámico.
    Se ejecuta cada vez que los datos cambian.
    """
    df = df_input.copy()
    
    # --- LIMPIEZA Y VALIDACIÓN ---
    # Convertir a numérico forzando errores a NaN (por si entra texto sucio)
    cols_check = ['Temperatura Celsius', 'Presión']
    for col in cols_check:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Eliminar filas donde los datos críticos sean NaN (evita fallos en KPI)
    df = df.dropna(subset=cols_check)
    
    BASE_VOLUME = 450.00
    
    # --- Fórmulas (Sin Modificaciones) ---
    df['Temperatura Fahrenheit'] = df['Temperatura Celsius'] * 1.8 + 32
    df['Temperature Over'] = df['Temperatura Fahrenheit']

    # Presión
    df['Vessel Pressure'] = df['Presión'] + 14.7

    # Factor Z
    t_term = 459.7 + df['Temperature Over']
    part1 = 0.000102297 - (0.000000192998 * t_term) + (0.00000000011836 * (t_term**2))
    df['Compressibility Factor (Z)'] = 1 + (part1 * df['Vessel Pressure']) - (0.0000000002217 * (df['Vessel Pressure']**2))

    # Factor Fv
    f_temp = 529.7 / (df['Temperature Over'] + 459.7)
    f_pres = df['Vessel Pressure'] / 14.7
    f_comp = 1.00049 / df['Compressibility Factor (Z)']
    f_exp_metal = 1 + (0.0000189 * (df['Temperature Over'] - 70))
    f_pres_efect = 1 + (0.00000074 * df['Vessel Pressure'])
    df['Volume Factor (Fv)'] = f_temp * f_pres * f_comp * f_exp_metal * f_pres_efect

    # Resultados
    df['Volume Helium ft3'] = (BASE_VOLUME * df['Volume Factor (Fv)'])
    df['Volume in Cubic Meters ( M3 )'] = df['Volume Helium ft3'] / 35.315

    # Consumo (Diff)
    # Importante: Asegurar orden antes del diff
    df = df.sort_values('Marca temporal')
    df['Diferencia M3'] = df['Volume in Cubic Meters ( M3 )'].diff().fillna(0)
    df['Consumo Absoluto M3'] = df['Diferencia M3'].abs()

    return df

# --- 4. GESTIÓN DE ESTADO (PERSISTENCIA DE EDICIONES) ---
if 'master_data' not in st.session_state:
    # Primera carga
    try:
        raw_df = fetch_raw_data()
        st.session_state.master_data = calculate_thermodynamics(raw_df)
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        st.stop()

# Trabajamos sobre el master en sesión
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

# --- 7. TABLA EDITOR INTERACTIVO ---
col_table, col_btn = st.columns([0.8, 0.2])

with col_table:
    st.subheader(f"Data Log: {view_option}")
    st.info("✍️ Modo Editor Habilitado: Modifica 'Temperatura' o 'Presión' y el gráfico se actualizará automáticamente.")

    # Configuración de Columnas (Bloqueo de campos calculados)
    column_cfg = {
        "Marca temporal": st.column_config.DatetimeColumn("Tiempo", disabled=True, format="D MMM YYYY, H:mm"),
        "Temperatura Celsius": st.column_config.NumberColumn("Temp (°C)", format="%.2f", step=0.1, required=True),
        "Presión": st.column_config.NumberColumn("Presión (PSI)", format="%.2f", step=0.1, required=True),
        # Campos Calculados - Solo lectura
        "Volume in Cubic Meters ( M3 )": st.column_config.NumberColumn("Volumen (M³)", format="%.4f", disabled=True),
        "Consumo Absoluto M3": st.column_config.NumberColumn("Consumo (M³)", format="%.4f", disabled=True),
        # Ocultamos columnas intermedias para limpieza visual si se desea, o las dejamos como disabled
        "Temperatura Fahrenheit": st.column_config.NumberColumn(disabled=True),
        "Vessel Pressure": st.column_config.NumberColumn(disabled=True),
        "Compressibility Factor (Z)": st.column_config.NumberColumn(disabled=True),
        "Volume Factor (Fv)": st.column_config.NumberColumn(disabled=True),
        "Diferencia M3": st.column_config.NumberColumn(disabled=True),
        "Temperature Over": st.column_config.NumberColumn(disabled=True),
        "Volume Helium ft3": st.column_config.NumberColumn(disabled=True),
    }

    edited_df = st.data_editor(
        df_vista,
        column_config=column_cfg,
        use_container_width=True,
        key="data_editor",
        num_rows="fixed" 
    )

    # LÓGICA DE ACTUALIZACIÓN AUTOMÁTICA
    if not edited_df.equals(df_vista):
        # 1. Actualizar el master con los datos editados (usando índices coincidentes)
        st.session_state.master_data.update(edited_df)
        
        # 2. Recalcular toda la termodinámica
        st.session_state.master_data = calculate_thermodynamics(st.session_state.master_data)
        
        # 3. Rerun para refrescar gráficos
        st.rerun()

with col_btn:
    st.write("")
    st.write("")
    st.write("")
    # Exportar datos (incluyendo ediciones)
    csv = edited_df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Descargar CSV", data=csv, file_name=f"Helio_Report_Edited_{view_option}.csv", mime='text/csv')

# --- 8. GRÁFICA DINÁMICA ---
st.subheader("Análisis de Tendencia")

# Preparar datos para Altair
plot_data = edited_df.copy()
plot_data['Alerta'] = plot_data['Consumo Absoluto M3'] > 2

chart = alt.Chart(plot_data).mark_line(point=True).encode(
    x=alt.X('Marca temporal:T', title='Marca de Tiempo'),
    y=alt.Y('Volume in Cubic Meters ( M3 ):Q', title='Volumen M3'),
    color=alt.condition(
        alt.datum.Alerta == True,
        alt.value('#FF0000'), 
        alt.value('#5271ff')
    ),
    tooltip=[
        alt.Tooltip('Marca temporal:T', format='%Y-%m-%d %H:%M'),
        alt.Tooltip('Temperatura Celsius:Q', title='Temp C'),
        alt.Tooltip('Presión:Q', title='Presión'),
        alt.Tooltip('Volume in Cubic Meters ( M3 ):Q', title='Volumen M3', format='.4f'),
        alt.Tooltip('Consumo Absoluto M3:Q', title='Consumo', format='.4f')
    ]
).interactive().properties(height=450)

st.altair_chart(chart, use_container_width=True)

if plot_data['Alerta'].any():
    st.error("🚨 Alerta: Se detectaron fluctuaciones de consumo superiores a 2 m³.")

# --- 9. FIRMA ---
st.markdown(
    """
    <div style="text-align: center; color: #6d6d6d; font-size: 0.9em; margin-top: 50px;">
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <h3 style="margin-bottom: 5px;">🚀 Monitor de Recuperación de Helio v1.1</h3>
        <p style="margin: 0;"><b>Developed by:</b> Master Engineer Erik Armenta</p>
        <p style="font-style: italic; color: #5271ff; font-weight: 500; margin-top: 5px;">
            "Accuracy is our signature, and innovation is our nature."
        </p>
    </div>
    """,
    unsafe_allow_html=True
)
