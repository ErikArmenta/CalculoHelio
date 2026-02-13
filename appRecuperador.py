# -*- coding: utf-8 -*-
"""
Created on Tue Jan 13 07:24:32 2026
@author: acer
"""

import streamlit as st
import pandas as pd
import altair as alt
import os
import requests
import google.generativeai as genai

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

# --- 3. SERVICIO DE ALERTAS EA INNOVATION ---
def enviar_alerta_whatsapp(mensaje: str):
    try:
        instance = str(st.secrets["WHA_INSTANCE"]).strip()
        token = str(st.secrets["WHA_TOKEN"]).strip()
        phone = str(st.secrets["WHA_PHONE"]).replace("+", "").strip()
        
        if not instance.startswith("instance"):
            instance = f"instance{instance}"
            
        url = f"https://api.ultramsg.com/{instance}/messages/chat"
        payload = {"token": token, "to": phone, "body": mensaje}
        headers = {'content-type': 'application/x-www-form-urlencoded'}
        response = requests.post(url, data=payload, headers=headers, timeout=10)
        return "✅ Alerta enviada" if response.status_code == 200 else f"❌ Error {response.status_code}"
    except Exception as e:
        return f"⚠️ Falla: {str(e)}"

# --- 4. LÓGICA TERMODINÁMICA ---
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
    df = df.sort_values('Marca temporal')
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

# --- 5. GESTIÓN DE ESTADO ---
if 'master_data' not in st.session_state:
    try:
        raw_df = fetch_raw_data()
        st.session_state.master_data = calculate_thermodynamics(raw_df)
    except Exception as e:
        st.error(f"Error cargando datos: {e}"); st.stop()

df_full = st.session_state.master_data

if view_option == "Últimas 24 Horas":
    cutoff = pd.Timestamp.now() - pd.Timedelta(hours=24)
    df_vista = df_full[df_full['Marca temporal'] >= cutoff].copy()
elif view_option == "Últimos 7 Días":
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=7)
    df_vista = df_full[df_full['Marca temporal'] >= cutoff].copy()
else:
    df_vista = df_full.copy()

# --- 6. KPI DASHBOARD (UNIFICADO) ---
st.title("🛡️ Helium Recovery System")
st.caption("Industrial Monitoring & Thermodynamic Calculation Engine")

if not df_vista.empty:
    last = df_vista.iloc[-1]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Volumen M3", f"{last['Volume in Cubic Meters ( M3 )']:.2f}", f"{last['Diferencia M3']:.4f}")
    c2.metric("Presión Absoluta", f"{last['Vessel Pressure']:.1f} PSIA")
    c3.metric("Factor Fv", f"{last['Volume Factor (Fv)']:.4f}")

    consumo_actual = last['Consumo Absoluto M3']
    alert_val = consumo_actual > 5
    
    if alert_val:
        if "ultima_alerta_enviada" not in st.session_state or st.session_state.ultima_alerta_enviada != last['Marca temporal']:
            msg_automatico = (
                f"🚨 *ALERTA AUTOMÁTICA EA*\n"
                f"Consumo Detectado: {consumo_actual:.2f} M3\n"
                f"Presión: {last['Vessel Pressure']:.1f} PSIA\n"
                f"Factor Z: {last['Compressibility Factor (Z)']:.6f}\n"
                f"Hora: {last['Marca temporal'].strftime('%H:%M:%S')}"
            )
            resultado_envio = enviar_alerta_whatsapp(msg_automatico)
            st.toast(resultado_envio)
            st.session_state.ultima_alerta_enviada = last['Marca temporal']

    c4.metric("Consumo Neto", f"{consumo_actual:.2f} M3", "⚠️ ALTA" if alert_val else "OK", delta_color="inverse" if alert_val else "normal")

st.divider()

# --- 7. TABLA EDITOR INTERACTIVO ---
col_table, col_btn = st.columns([0.8, 0.2])
with col_table:
    st.subheader(f"Data Log: {view_option}")
    st.info("✍️ **Modo Editor Habilitado**")
    column_cfg = {
        "Marca temporal": st.column_config.DatetimeColumn("Tiempo (Editable)", format="D MMM YYYY, H:mm", required=True),
        "Temperatura Celsius": st.column_config.NumberColumn("Temp (°C)", format="%.2f", step=0.1),
        "Presión": st.column_config.NumberColumn("Presión (PSI)", format="%.2f", step=0.1),
        "Volume in Cubic Meters ( M3 )": st.column_config.NumberColumn("Volumen (M³)", format="%.4f", disabled=True),
        "Consumo Absoluto M3": st.column_config.NumberColumn("Consumo (M³)", format="%.4f", disabled=True),
    }
    edited_df = st.data_editor(df_vista, column_config=column_cfg, use_container_width=True, key="data_editor", num_rows="fixed")
    if not edited_df.equals(df_vista):
        st.session_state.master_data.update(edited_df)
        st.session_state.master_data = calculate_thermodynamics(st.session_state.master_data)
        st.rerun()

with col_btn:
    st.write(""); st.write(""); st.write("")
    csv = df_full.to_csv(index=False).encode('utf-8')
    st.download_button(label="💾 Descargar CSV", data=csv, file_name=f"Helium_Report.csv", mime='text/csv')

# --- 8. GRÁFICAS ---
st.subheader("Análisis de Tendencia")
plot_data = edited_df.copy()
plot_data['Alerta'] = plot_data['Consumo Absoluto M3'] > 5
chart = alt.Chart(plot_data).mark_line(point=True).encode(
    x=alt.X('Marca temporal:T', title='Tiempo'),
    y=alt.Y('Volume in Cubic Meters ( M3 ):Q', title='Volumen M3'),
    color=alt.condition(alt.datum.Alerta == True, alt.value('#FF0000'), alt.value('#5271ff')),
    tooltip=['Marca temporal', 'Temperatura Celsius', 'Presión', 'Volume in Cubic Meters ( M3 )', 'Consumo Absoluto M3']
).interactive().properties(height=450)
st.altair_chart(chart, use_container_width=True)

st.subheader("Correlación de Variables")
df_melted = plot_data.melt(id_vars=['Marca temporal'], value_vars=['Presión', 'Volume in Cubic Meters ( M3 )', 'Temperatura Fahrenheit'], var_name='Variable', value_name='Valor')
color_scale = alt.Scale(domain=['Presión', 'Volume in Cubic Meters ( M3 )', 'Temperatura Fahrenheit'], range=['#FF0000', '#0000FF', '#FFD700'])
multi_chart = alt.Chart(df_melted).mark_line(point=True).encode(
    x=alt.X('Marca temporal:T'), y=alt.Y('Valor:Q', scale=alt.Scale(zero=False)),
    color=alt.Color('Variable:N', scale=color_scale), tooltip=['Marca temporal', 'Variable', 'Valor']
).interactive().properties(height=450)
st.altair_chart(multi_chart, use_container_width=True)

# --- 9. FIRMA ---
st.markdown(
    """<div style="text-align: center; color: #6d6d6d; font-size: 0.9em; margin-top: 50px;">
    <hr><h3 style="margin-bottom: 5px;">🚀 Monitor de Recuperación de Helio v1.4</h3>
    <p><b>Developed by:</b> Master Engineer Erik Armenta</p>
    <p style="font-style: italic; color: #5271ff; font-weight: 500;">"Accuracy is our signature, and innovation is our nature."</p>
    </div>""", unsafe_allow_html=True
)

# --- 10. AI AGENT TOOLS ---
def calculadora_expert_ea(temp_c: float, presion_psi: float):
    BASE_VOLUME = 450.00
    temp_f = temp_c * 1.8 + 32; vessel_pres = presion_psi + 14.7; t_term = 459.7 + temp_f
    part1 = 0.000102297 - (0.000000192998 * t_term) + (0.00000000011836 * (t_term**2))
    z_factor = 1 + (part1 * vessel_pres) - (0.0000000002217 * (vessel_pres**2))
    f_temp = 529.7 / (temp_f + 459.7); f_pres = vessel_pres / 14.7
    f_comp = 1.00049 / z_factor; f_exp_metal = 1 + (0.0000189 * (temp_f - 70))
    f_pres_efect = 1 + (0.00000074 * vessel_pres)
    fv = f_temp * f_pres * f_comp * f_exp_metal * f_pres_efect
    vol_m3 = (BASE_VOLUME * fv) / 35.315
    return {"Factor_Z": round(z_factor, 6), "Factor_Fv": round(fv, 4), "Volumen_M3": round(vol_m3, 4)}

def crear_grafica_agente(variable_y: str, variable_x: str = 'Marca temporal'):
    if variable_y in df_vista.columns:
        chart = alt.Chart(df_vista).mark_line(point=True, color='#5271ff').encode(
            x=alt.X(f'{variable_x}:T' if 'temporal' in variable_x else f'{variable_x}:Q'),
            y=alt.Y(f'{variable_y}:Q', scale=alt.Scale(zero=False)), tooltip=[variable_x, variable_y]
        ).interactive().properties(height=350)
        st.altair_chart(chart, use_container_width=True)
        return f"Gráfica de {variable_y} generada."
    return "Error: Variable no encontrada."

def analizar_tendencias_historicas(metrica: str):
    if metrica in df_full.columns:
        return {"Metrica": metrica, "Promedio": round(df_full[metrica].mean(), 2), "Max": round(df_full[metrica].max(), 2), "Total": len(df_full)}
    return "Métrica no válida."

# AI CONFIGURATION
try:
    api_key = st.secrets.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    modelo_sel = next((m for m in modelos if '1.5-flash' in m), modelos[0])
    model = genai.GenerativeModel(
        model_name=modelo_sel,
        tools=[calculadora_expert_ea, crear_grafica_agente, analizar_tendencias_historicas, enviar_alerta_whatsapp],
        system_instruction="Eres el Agente Senior de EA Innovation. 'Accuracy is our signature'. Ante anomalías, envía alertas de WhatsApp."
    )
    st.sidebar.success(f"IA Operativa: {modelo_sel.split('/')[-1]}")
except Exception as e:
    st.error(f"Error IA: {e}")

# CHAT INTERFACE
st.divider(); st.header("🤖 EA Innovation Agent")
if "messages" not in st.session_state: st.session_state.messages = []
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if chat_input := st.chat_input("¿Qué análisis técnico requiere?"):
    st.session_state.messages.append({"role": "user", "content": chat_input})
    with st.chat_message("user"): st.markdown(chat_input)
    with st.chat_message("assistant"):
        try:
            chat = model.start_chat(enable_automatic_function_calling=True)
            contexto = f"DATOS RECIENTES:\n{df_vista.tail(5).to_string(index=False)}\n\nPREGUNTA: {chat_input}"
            response = chat.send_message(contexto)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e: st.error(f"Error: {e}")





















