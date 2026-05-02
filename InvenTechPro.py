# =============================================================================
# INVENTECH PRO — SISTEMA DE CONTROL DE INVENTARIO PARA METALMECÁNICA
# Desarrollado con: Python · Streamlit · Supabase · Groq AI
# =============================================================================
# DESCRIPCIÓN GENERAL:
#   Aplicación web de gestión de inventario con autenticación de usuarios,
#   panel de control con métricas en tiempo real, CRUD completo de productos,
#   categorías, proveedores, órdenes de compra y operaciones de almacén.
#   Incluye un asistente de IA (ARIA) integrado en la barra lateral.
# =============================================================================


# ─────────────────────────────────────────────────────────────────────────────
# SECCIÓN 1: IMPORTACIONES
# Descripción: Se importan todas las librerías necesarias para el proyecto.
#   - streamlit: framework principal para construir la interfaz web.
#   - supabase: cliente para conectarse a la base de datos en la nube.
#   - pandas: manipulación y visualización de datos en tablas.
#   - datetime / date: manejo de fechas para registros y formularios.
#   - hashlib: para cifrar contraseñas con SHA-256.
#   - groq: cliente de IA para el asistente ARIA (modelo LLaMA 3).
#   - json: serialización de datos para el contexto del chatbot.
# ─────────────────────────────────────────────────────────────────────────────
import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import date, datetime
import hashlib
from groq import Groq
import json


# ─────────────────────────────────────────────────────────────────────────────
# SECCIÓN 2: CONFIGURACIÓN GLOBAL
# Descripción: Variables de entorno y configuración inicial de la aplicación.
#   - SUPABASE_URL / SUPABASE_KEY: credenciales para conectarse a la base
#     de datos Supabase (backend como servicio).
#   - GROQ_API_KEY: clave para acceder al modelo de lenguaje de Groq.
#   - BG_IMAGE: URL de la imagen de fondo que aparece en la pantalla de login.
#   - st.set_page_config(): configura el título, ícono y layout de la app.
# ─────────────────────────────────────────────────────────────────────────────
SUPA_URL = st.secrets["SUPA_URL"]
SUPA_KEY = st.secrets["SUPA_KEY"]
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
BG_IMAGE      = "https://i.imgur.com/BYJcOv2.jpeg"

st.set_page_config(
    page_title="InvenTech Pro — Metalmecánica",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─────────────────────────────────────────────────────────────────────────────
# SECCIÓN 3: CONEXIÓN A SUPABASE
# Descripción: Se crea el cliente de Supabase usando las credenciales definidas.
#   - @st.cache_resource: decorador que cachea el cliente para no reconectarse
#     en cada recarga de página (mejora el rendimiento).
#   - El cliente 'supabase' es el objeto central que permite hacer todas las
#     operaciones de base de datos (SELECT, INSERT, UPDATE, DELETE).
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()


# ─────────────────────────────────────────────────────────────────────────────
# SECCIÓN 4: FONDO DE PANTALLA CONDICIONAL (solo en login)
# Descripción: Se aplica un fondo con imagen y overlay oscuro únicamente cuando
#   el usuario NO está autenticado (pantalla de inicio de sesión).
#   Usa CSS inyectado con st.markdown() y unsafe_allow_html=True.
#   El overlay usa un gradiente semitransparente para mejorar la legibilidad.
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state.get("authenticated"):
    st.markdown(f"""
    <style>
    [data-testid="stAppViewContainer"] {{
        background-image: url('{BG_IMAGE}') !important;
        background-size: cover !important;
        background-position: center !important;
        background-attachment: fixed !important;
    }}
    [data-testid="stAppViewContainer"]::before {{
        content: '';
        position: fixed;
        inset: 0;
        background: linear-gradient(135deg,
            rgba(5,10,22,0.90) 0%,
            rgba(8,14,30,0.82) 50%,
            rgba(3,8,20,0.92) 100%);
        z-index: 0;
        pointer-events: none;
    }}
    [data-testid="stMain"] {{ position: relative; z-index: 1; }}
    .main .block-container {{ padding: 0 !important; }}
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SECCIÓN 5: ESTADO DE SESIÓN (Session State)
# Descripción: Streamlit recarga el script completo con cada interacción.
#   st.session_state actúa como memoria persistente entre recargas.
#   Se inicializan las variables clave solo si aún no existen:
#   - authenticated: indica si el usuario ha iniciado sesión (bool).
#   - login_error / login_success: mensajes de feedback en el formulario.
#   - chat_history: historial de mensajes del chatbot ARIA.
# ─────────────────────────────────────────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "login_error" not in st.session_state:
    st.session_state.login_error = ""
if "login_success" not in st.session_state:
    st.session_state.login_success = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "assistant", "content": "Hola, soy ARIA. ¿En qué puedo ayudarte con el inventario?"}
    ]


# ─────────────────────────────────────────────────────────────────────────────
# SECCIÓN 6: ESTILOS CSS GLOBALES
# Descripción: Hoja de estilos personalizada inyectada en la app para lograr
#   el diseño oscuro y moderno (dark theme). Se definen:
#   - Variables CSS (:root) con la paleta de colores y radios de bordes.
#   - Estilos para componentes de Streamlit: inputs, botones, tablas,
#     tabs, alertas, sidebar, tarjetas KPI, burbujas del chat, etc.
#   - Fuentes personalizadas de Google Fonts (Syne + Inter).
#   - Clases utilitarias: .kpi-grid, .kpi-card, .alert-row, .empty-state, etc.
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap');

:root {{
    --bg-base:      #0f0f0f;
    --bg-surface:   #1a1a1a;
    --bg-overlay:   #242424;
    --bg-hover:     #2a2a2a;
    --border:       #2e2e2e;
    --border-light: #3e3e3e;
    --brand:        #3ecf8e;
    --brand-dim:    rgba(62,207,142,0.12);
    --brand-border: rgba(62,207,142,0.3);
    --text:         #ededed;
    --text-muted:   #a0a0a0;
    --text-faint:   #666;
    --red:          #f54b4b;
    --red-dim:      rgba(245,75,75,0.1);
    --yellow:       #f5a623;
    --yellow-dim:   rgba(245,166,35,0.1);
    --blue:         #4a9eff;
    --blue-dim:     rgba(74,158,255,0.1);
    --radius-sm:    6px;
    --radius-md:    10px;
    --radius-lg:    14px;
}}

*, *::before, *::after {{ box-sizing: border-box; }}

html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    color: var(--text) !important;
}}

#MainMenu, footer, header, [data-testid="stToolbar"] {{ display: none !important; }}
[data-testid="stDecoration"] {{ display: none !important; }}
[data-testid="collapsedControl"] {{ display: none !important; }}
button[kind="header"] {{ display: none !important; }}
[data-testid="stSidebarCollapseButton"] {{ display: none !important; }}

[data-testid="stSidebar"] {{
    background: var(--bg-surface) !important;
    border-right: 1px solid var(--border) !important;
    width: 240px !important;
}}
[data-testid="stSidebar"] > div:first-child {{ padding: 0 !important; }}
[data-testid="stSidebar"] * {{ color: var(--text) !important; }}
section[data-testid="stSidebar"] {{ min-width: 240px !important; max-width: 240px !important; }}

.stRadio > div {{ gap: 2px !important; }}
.stRadio label {{
    display: flex !important;
    align-items: center !important;
    padding: 8px 12px !important;
    border-radius: var(--radius-sm) !important;
    font-size: 13.5px !important;
    font-weight: 400 !important;
    color: var(--text-muted) !important;
    cursor: pointer !important;
    transition: all 0.15s ease !important;
    margin: 0 !important;
    width: 100% !important;
}}
.stRadio label:hover {{ background: var(--bg-overlay) !important; color: var(--text) !important; }}
.stRadio [data-testid="stMarkdownContainer"] p {{ margin: 0 !important; }}

div[data-baseweb="radio"] > label {{ position: relative !important; }}
div[data-baseweb="radio"] > label > div:first-child {{ display: none !important; }}
div[data-baseweb="radio"] > label > div:first-child * {{ display: none !important; }}
[data-testid="stSidebar"] [role="radio"] {{ display: none !important; }}
[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] {{ gap: 0 !important; }}

div[data-baseweb="radio"] > label:has(input:checked) {{
    background: var(--bg-overlay) !important;
    color: var(--text) !important;
    font-weight: 500 !important;
}}
div[data-baseweb="radio"] > label:has(input:checked)::before {{
    content: '';
    position: absolute;
    left: 0; top: 4px; bottom: 4px;
    width: 2px;
    background: var(--brand);
    border-radius: 2px;
}}

.stTextInput input, .stTextArea textarea, .stNumberInput input {{
    background: var(--bg-overlay) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: var(--radius-sm) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13.5px !important;
    padding: 8px 12px !important;
    transition: border-color 0.15s !important;
}}
.stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {{
    border-color: var(--brand) !important;
    box-shadow: 0 0 0 2px var(--brand-dim) !important;
    outline: none !important;
}}
.stTextInput label, .stTextArea label, .stNumberInput label,
.stSelectbox label, .stRadio label span {{
    color: var(--text-muted) !important;
    font-size: 12.5px !important;
    font-weight: 500 !important;
}}

.stSelectbox > div > div {{
    background: var(--bg-overlay) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text) !important;
    font-size: 13.5px !important;
}}
.stSelectbox > div > div:focus-within {{ border-color: var(--brand) !important; }}
[data-baseweb="select"] [data-baseweb="popover"] {{
    background: var(--bg-overlay) !important;
    border: 1px solid var(--border) !important;
}}

.stButton button {{
    background: var(--bg-overlay) !important;
    color: var(--text) !important;
    border: 1px solid var(--border-light) !important;
    border-radius: var(--radius-sm) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 6px 14px !important;
    transition: all 0.15s !important;
    height: auto !important;
}}
.stButton button:hover {{
    background: var(--bg-hover) !important;
    border-color: var(--border-light) !important;
}}
[data-testid="stSidebar"] .stButton button {{
    background: transparent !important;
    color: var(--text-muted) !important;
    border: 1px solid #2a2a2a !important;
    font-size: 12.5px !important;
    font-weight: 400 !important;
    transition: all 0.2s !important;
}}
[data-testid="stSidebar"] .stButton button:hover {{
    background: var(--red-dim) !important;
    color: var(--red) !important;
    border-color: rgba(245,75,75,0.3) !important;
}}
.stButton button[kind="primary"] {{
    background: var(--brand) !important;
    color: #0f0f0f !important;
    border-color: var(--brand) !important;
    font-weight: 600 !important;
}}
.stButton button[kind="primary"]:hover {{
    background: #35bb7d !important;
    border-color: #35bb7d !important;
}}
[data-testid="stSidebar"] .stFormSubmitButton button {{
    height: 36px !important;
    padding: 0 10px !important;
    font-size: 12.5px !important;
}}
[data-testid="stSidebar"] .stFormSubmitButton:first-child button {{
    background: var(--brand) !important;
    color: #0f0f0f !important;
    border-color: var(--brand) !important;
    font-weight: 600 !important;
}}
[data-testid="stSidebar"] .stFormSubmitButton:first-child button:hover {{
    background: #35bb7d !important;
    border-color: #35bb7d !important;
}}
[data-testid="stSidebar"] .stFormSubmitButton:last-child button {{
    background: transparent !important;
    color: #555 !important;
    border-color: #2a2a2a !important;
    font-size: 14px !important;
}}
[data-testid="stSidebar"] .stFormSubmitButton:last-child button:hover {{
    background: #1e1e1e !important;
    color: var(--red) !important;
    border-color: var(--red) !important;
}}

.stDataFrame {{
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
    overflow: hidden !important;
}}
.stDataFrame table {{ font-size: 13px !important; }}
.stDataFrame thead th {{
    background: var(--bg-overlay) !important;
    color: var(--text-muted) !important;
    font-size: 11.5px !important;
    font-weight: 500 !important;
    letter-spacing: 0.5px !important;
    text-transform: uppercase !important;
    border-bottom: 1px solid var(--border) !important;
}}
.stDataFrame tbody td {{
    color: var(--text) !important;
    border-bottom: 1px solid var(--border) !important;
    font-size: 13px !important;
}}
.stDataFrame tbody tr:hover td {{ background: var(--bg-hover) !important; }}

.stTabs [data-baseweb="tab-list"] {{
    background: transparent !important;
    border-bottom: 1px solid var(--border) !important;
    gap: 0 !important;
}}
.stTabs [data-baseweb="tab"] {{
    background: transparent !important;
    color: var(--text-muted) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13.5px !important;
    font-weight: 500 !important;
    padding: 8px 16px !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
}}
.stTabs [data-baseweb="tab-list"] [aria-selected="true"] {{
    color: var(--text) !important;
    border-bottom: 2px solid var(--brand) !important;
    background: transparent !important;
}}
.stTabs [data-baseweb="tab-highlight"] {{
    background: var(--brand) !important;
}}
.stTabs [data-baseweb="tab-panel"] {{ padding-top: 20px !important; }}

.stSuccess > div {{ background: rgba(62,207,142,0.08) !important; border: 1px solid rgba(62,207,142,0.25) !important; border-radius: var(--radius-sm) !important; color: #3ecf8e !important; }}
.stError   > div {{ background: var(--red-dim) !important; border: 1px solid rgba(245,75,75,0.3) !important; border-radius: var(--radius-sm) !important; }}
.stWarning > div {{ background: var(--yellow-dim) !important; border: 1px solid rgba(245,166,35,0.3) !important; border-radius: var(--radius-sm) !important; }}
.stInfo    > div {{ background: var(--blue-dim) !important; border: 1px solid rgba(74,158,255,0.3) !important; border-radius: var(--radius-sm) !important; }}

.streamlit-expanderHeader {{
    background: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    font-size: 13.5px !important;
    color: var(--text-muted) !important;
}}
.streamlit-expanderContent {{
    border: 1px solid var(--border) !important;
    border-top: none !important;
    background: var(--bg-surface) !important;
}}

hr {{ border-color: var(--border) !important; margin: 12px 0 !important; }}
::-webkit-scrollbar {{ width: 4px; height: 4px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: var(--border-light); border-radius: 2px; }}
.main .block-container {{ padding: 28px 32px 40px 32px !important; max-width: 100% !important; }}

.kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 28px; }}
.kpi-card {{ background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 20px 22px; position: relative; overflow: hidden; transition: border-color 0.2s; }}
.kpi-card:hover {{ border-color: var(--border-light); }}
.kpi-label {{ font-size: 11.5px; font-weight: 500; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 10px; }}
.kpi-value {{ font-size: 28px; font-weight: 700; line-height: 1; color: var(--text); }}
.kpi-accent {{ width: 28px; height: 3px; border-radius: 2px; margin-top: 12px; }}
.kpi-icon {{ font-size: 22px; position: absolute; top: 16px; right: 16px; opacity: 0.3; }}
.kpi-card.green  .kpi-value {{ color: var(--brand); }} .kpi-card.red    .kpi-value {{ color: var(--red); }}
.kpi-card.blue   .kpi-value {{ color: var(--blue); }} .kpi-card.yellow .kpi-value {{ color: var(--yellow); }}
.kpi-card.green  .kpi-accent {{ background: var(--brand); }} .kpi-card.red    .kpi-accent {{ background: var(--red); }}
.kpi-card.blue   .kpi-accent {{ background: var(--blue); }} .kpi-card.yellow .kpi-accent {{ background: var(--yellow); }}

.page-header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; padding-bottom: 18px; border-bottom: 1px solid var(--border); }}
.page-title {{ font-size: 20px; font-weight: 600; color: var(--text); margin: 0; letter-spacing: -0.3px; }}
.page-subtitle {{ font-size: 13px; color: var(--text-muted); margin: 4px 0 0 0; }}
.user-chip {{ display: flex; align-items: center; gap: 10px; background: var(--bg-surface); border: 1px solid var(--border); border-radius: 8px; padding: 8px 14px; }}
.user-avatar {{ width: 28px; height: 28px; background: var(--brand-dim); border: 1px solid var(--brand-border); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; color: var(--brand); }}
.user-info-name {{ font-size: 13px; font-weight: 500; color: var(--text); }}
.user-info-role {{ font-size: 11px; color: var(--text-muted); margin-top: 1px; }}

.alert-row {{ display: flex; align-items: center; gap: 10px; background: var(--red-dim); border: 1px solid rgba(245,75,75,0.25); border-radius: var(--radius-sm); padding: 10px 14px; margin: 6px 0; font-size: 13px; }}
.alert-dot {{ width: 6px; height: 6px; border-radius: 50%; background: var(--red); flex-shrink: 0; }}
.alert-text {{ color: var(--text); flex: 1; }}
.alert-badge {{ background: rgba(245,75,75,0.15); border: 1px solid rgba(245,75,75,0.3); border-radius: 4px; padding: 2px 7px; font-size: 11px; color: var(--red); font-weight: 500; }}

.section-label {{ font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; color: var(--text-faint); margin: 20px 0 10px 0; padding: 0 2px; }}

.sidebar-brand {{ display: flex; align-items: center; gap: 10px; padding: 18px 16px 14px 16px; border-bottom: 1px solid var(--border); margin-bottom: 8px; }}
.sidebar-brand-icon {{ width: 28px; height: 28px; background: var(--brand); border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 13px; flex-shrink: 0; }}
.sidebar-brand-name {{ font-size: 14px; font-weight: 700; color: var(--text); letter-spacing: -0.2px; }}
.sidebar-brand-sub {{ font-size: 10.5px; color: var(--text-muted); margin-top: 1px; }}
.sidebar-user-block {{ margin: 4px 8px 8px 8px; padding: 10px 12px; background: var(--bg-overlay); border: 1px solid var(--border); border-radius: var(--radius-sm); display: flex; align-items: center; gap: 10px; }}
.sidebar-avatar {{ width: 28px; height: 28px; background: var(--brand-dim); border: 1px solid var(--brand-border); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; color: var(--brand); flex-shrink: 0; }}
.sidebar-user-name {{ font-size: 13px; font-weight: 500; color: var(--text); }}
.sidebar-user-email {{ font-size: 11px; color: var(--text-muted); margin-top: 1px; }}
.sidebar-role-badge {{ display: inline-flex; align-items: center; background: var(--brand-dim); border: 1px solid var(--brand-border); border-radius: 4px; padding: 1px 7px; font-size: 10.5px; color: var(--brand); font-weight: 500; margin-top: 4px; }}
.sidebar-nav-label {{ font-size: 10.5px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.7px; color: var(--text-faint); padding: 10px 16px 4px 16px; }}
.sidebar-nav-wrap {{ padding: 0 8px; }}

@keyframes pulse-dot {{
    0%,100% {{ opacity: 1; }}
    50%      {{ opacity: 0.4; }}
}}
.chat-bubble-ai {{
    align-self: flex-start;
    background: var(--bg-overlay);
    border: 1px solid var(--border);
    color: var(--text);
    border-radius: 11px 11px 11px 3px;
    padding: 9px 12px;
    font-size: 12.5px;
    max-width: 86%;
    line-height: 1.5;
    word-wrap: break-word;
}}
.chat-bubble-user {{
    align-self: flex-end;
    background: var(--brand);
    color: #0f0f0f;
    border-radius: 11px 11px 3px 11px;
    padding: 9px 12px;
    font-size: 12.5px;
    font-weight: 500;
    max-width: 82%;
    word-wrap: break-word;
}}
[data-testid="stVerticalBlockBorderWrapper"] ::-webkit-scrollbar-track {{ background: transparent; }}
[data-testid="stVerticalBlockBorderWrapper"] ::-webkit-scrollbar-thumb {{ background: #2e2e2e; border-radius: 2px; }}
[data-testid="stSidebar"] [data-testid="stTextInput"] input {{ outline: none !important; }}
[data-testid="stSidebar"] .stForm [data-testid="InputInstructions"] {{ display: none !important; }}
.empty-state {{
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px 20px;
    border: 1px dashed var(--border-light);
    border-radius: var(--radius-md);
    margin: 10px 0;
}}
.empty-state-icon {{ font-size: 32px; opacity: 0.4; margin-bottom: 12px; }}
.empty-state-text {{ font-size: 13.5px; color: var(--text-muted); margin: 0; }}
.empty-state-sub {{ font-size: 12px; color: var(--text-faint); margin-top: 4px; }}
</style>
""", unsafe_allow_html=True)


# =============================================================================
# SECCIÓN 7: FUNCIONES AUXILIARES DE BASE DE DATOS
# Descripción: Funciones genéricas que encapsulan las operaciones CRUD contra
#   Supabase. Usar funciones reutilizables evita repetir código en cada módulo.
# =============================================================================

def fetch(table: str, select: str = "*") -> pd.DataFrame:
    """
    Lee registros de una tabla de Supabase y los retorna como DataFrame.
    Parámetros:
        table  → nombre de la tabla (ej: "producto").
        select → columnas a traer, permite JOINs implícitos (ej: "*, categoria(nombre)").
    Retorna: DataFrame vacío si no hay datos.
    """
    res = supabase.table(table).select(select).execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

def insert(table: str, data: dict):
    """
    Inserta un nuevo registro en la tabla indicada.
    Parámetros:
        table → nombre de la tabla.
        data  → diccionario con los campos y valores a insertar.
    """
    return supabase.table(table).insert(data).execute()

def update(table: str, row_id: str, data: dict):
    """
    Actualiza un registro existente identificado por su 'id'.
    Parámetros:
        table  → nombre de la tabla.
        row_id → valor del campo 'id' del registro a modificar.
        data   → diccionario con los campos a actualizar.
    """
    return supabase.table(table).update(data).eq("id", row_id).execute()

def delete(table: str, row_id: str):
    """
    Elimina un registro por su 'id'.
    Parámetros:
        table  → nombre de la tabla.
        row_id → valor del campo 'id' del registro a eliminar.
    """
    return supabase.table(table).delete().eq("id", row_id).execute()

def ok(label: str):
    """Muestra un mensaje de éxito verde en pantalla."""
    st.success(f"✓ {label}")

def err(e):
    """Muestra un mensaje de error rojo con el detalle de la excepción."""
    st.error(f"Error: {e}")

def empty_state(icon: str, text: str, sub: str = ""):
    """
    Renderiza un bloque visual de 'estado vacío' cuando no hay datos.
    Útil para reemplazar tablas vacías con un mensaje amigable.
    """
    sub_html = f'<div class="empty-state-sub">{sub}</div>' if sub else ""
    st.markdown(f"""
    <div class="empty-state">
        <div class="empty-state-icon">{icon}</div>
        <div class="empty-state-text">{text}</div>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)

def confirm_key(action: str, row_id: str) -> str:
    """
    Genera una clave única para el estado de confirmación de eliminación.
    Evita colisiones entre múltiples botones de eliminar en la misma página.
    Ejemplo: confirm_key("del_prod", "abc123") → "confirm_del_prod_abc123"
    """
    return f"confirm_{action}_{row_id}"

def hash_password(password: str) -> str:
    """
    Cifra una contraseña usando el algoritmo SHA-256.
    NOTA: SHA-256 no es salteado; para producción real se debería usar bcrypt.
    """
    return hashlib.sha256(password.encode()).hexdigest()

def log_auditoria(accion: str, tabla: str, descripcion: str):
    """
    Registra en la tabla 'auditoria' cada acción relevante del usuario.
    Parámetros:
        accion      → tipo de acción (AGREGAR, EDITAR, ELIMINAR).
        tabla       → tabla afectada por la acción.
        descripcion → texto libre que explica qué se hizo exactamente.
    El error se silencia (pass) para no interrumpir el flujo principal.
    """
    user   = st.session_state.get("user_email", "desconocido")
    nombre = st.session_state.get("user_name", "—")
    try:
        supabase.table("auditoria").insert({
            "usuario_email":  user,
            "usuario_nombre": nombre,
            "accion":         accion,
            "tabla_afectada": tabla,
            "descripcion":    descripcion,
            "fecha":          datetime.utcnow().isoformat(),
        }).execute()
    except Exception:
        pass


# =============================================================================
# SECCIÓN 8: ASISTENTE DE IA — ARIA (Chatbot con Groq + LLaMA 3)
# =============================================================================

def get_inventory_context() -> str:
    """
    Recopila datos actuales del inventario para dárselos como contexto al modelo
    de lenguaje. Esto permite que ARIA responda preguntas específicas del almacén,
    como "¿qué productos están bajo stock?" sin acceder directamente a la BD.
    Retorna un string con: total de productos, movimientos, órdenes pendientes
    y la lista de productos críticos (stock <= mínimo), hasta 10.
    """
    try:
        productos  = fetch("producto")
        movs       = fetch("movimiento")
        ordenes    = fetch("orden_compra")
        bajo_stock = []
        if not productos.empty:
            bajo = productos[productos["stock_actual"] <= productos["stock_minimo"]]
            bajo_stock = bajo[["codigo","nombre","stock_actual","stock_minimo"]].to_dict("records")
        ctx = f"""
Sistema: Control de Inventario — Metalmecánica
Productos registrados: {len(productos)}
Movimientos totales: {len(movs)}
Órdenes de compra pendientes: {len(ordenes[ordenes["estado"] == "pendiente"]) if not ordenes.empty else 0}
Productos bajo stock mínimo ({len(bajo_stock)}):
{json.dumps(bajo_stock[:10], ensure_ascii=False, indent=2)}
        """
        return ctx.strip()
    except Exception:
        return "Datos del inventario no disponibles en este momento."

def chat_with_ai(user_message: str, history: list) -> str:
    """
    Envía el mensaje del usuario al modelo LLaMA 3 (via Groq) y retorna
    la respuesta del asistente ARIA.
    Lógica:
        1. Construye el prompt de sistema con el contexto del inventario.
        2. Agrega los últimos 6 mensajes del historial para dar continuidad.
        3. Agrega el mensaje actual del usuario.
        4. Llama a la API de Groq y retorna el texto de respuesta.
    En caso de error, retorna un mensaje descriptivo sin romper la app.
    """
    try:
        client  = Groq(api_key=GROQ_API_KEY)
        inv_ctx = get_inventory_context()
        messages = [
            {
                "role": "system",
                "content": f"""Eres ARIA, asistente de inventario para una empresa metalmecánica.
Responde en español, de forma concisa y profesional. Contexto actual:\n{inv_ctx}"""
            }
        ]
        for h in history[-6:]:
            if h["role"] in ("user", "assistant"):
                if not messages[1:] and h["role"] == "assistant":
                    continue
                messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": user_message})
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=600,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error al conectar con el asistente: {str(e)[:80]}"

def render_chatbot():
    """
    Renderiza el widget del chatbot ARIA en la barra lateral.
    Componentes:
        - Indicador de estado "en línea" con punto verde animado.
        - Contenedor scrollable con el historial de mensajes (burbujas).
        - Formulario con campo de texto y botones 'Enviar' y 'Limpiar' (🗑).
    Flujo de interacción:
        1. El usuario escribe y presiona 'Enviar'.
        2. El mensaje se agrega al historial.
        3. Se llama a chat_with_ai() para obtener la respuesta.
        4. La respuesta se agrega al historial y se recarga la app.
    """
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "assistant", "content": "Hola, soy ARIA. ¿En qué puedo ayudarte con el inventario?"}
        ]

    with st.sidebar:
        st.markdown("---")
        st.markdown("""
        <div style="display:flex;align-items:center;gap:8px;padding:4px 0 8px 0;">
            <div style="width:8px;height:8px;border-radius:50%;background:#3ecf8e;
                box-shadow:0 0 6px #3ecf8e;flex-shrink:0;"></div>
            <div style="font-size:13px;font-weight:600;color:#ededed;">Asistente ARIA</div>
            <div style="font-size:10.5px;color:#666;margin-left:auto;">en línea</div>
        </div>
        """, unsafe_allow_html=True)

        chat_container = st.container(height=220, border=False)
        with chat_container:
            for msg in st.session_state.chat_history[-10:]:
                align  = "flex-end" if msg["role"] == "user" else "flex-start"
                bg     = "#3ecf8e" if msg["role"] == "user" else "#1e1e1e"
                color  = "#0f0f0f" if msg["role"] == "user" else "#ededed"
                radius = "11px 11px 3px 11px" if msg["role"] == "user" else "11px 11px 11px 3px"
                text   = msg["content"].replace("<","&lt;").replace(">","&gt;")
                st.markdown(f"""
                <div style="display:flex;justify-content:{align};margin:6px 0;">
                    <div style="background:{bg};color:{color};border-radius:{radius};
                        padding:9px 13px;font-size:12.5px;max-width:88%;
                        line-height:1.6;word-wrap:break-word;
                        border:1px solid {'rgba(62,207,142,0.15)' if msg['role']=='user' else '#2a2a2a'};">
                        {text}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("""
        <div style="border-top:1px solid #1e1e1e;margin:6px 0 10px 0;"></div>
        """, unsafe_allow_html=True)
        with st.form("aria_form", clear_on_submit=True):
            user_input = st.text_input("", placeholder="Pregunta a ARIA...",
                                       label_visibility="collapsed", key="aria_input")
            col1, col2 = st.columns([3, 1])
            with col1:
                submitted = st.form_submit_button("Enviar →", use_container_width=True, type="primary")
            with col2:
                clear = st.form_submit_button("🗑", use_container_width=True)

        if clear:
            st.session_state.chat_history = [
                {"role": "assistant", "content": "Hola, soy ARIA. ¿En qué puedo ayudarte con el inventario?"}
            ]
            st.rerun()

        if submitted and user_input.strip():
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            with st.spinner("ARIA está pensando..."):
                reply = chat_with_ai(user_input, st.session_state.chat_history[:-1])
            st.session_state.chat_history.append({"role": "assistant", "content": reply})
            st.rerun()


# =============================================================================
# SECCIÓN 9: PANTALLA DE LOGIN Y REGISTRO
# =============================================================================

def render_login():
    """
    Renderiza la pantalla de inicio de sesión y registro de usuarios.
    Soporta dos métodos de autenticación:
        A) Usuario del sistema: credenciales personalizadas guardadas en la
           tabla 'usuarios' de Supabase, con hash SHA-256.
        B) Cuenta Supabase Auth: autenticación nativa de Supabase usando
           email y contraseña (con confirmación por correo al registrarse).
    Pestañas:
        - "Iniciar sesión": formulario de login para el método seleccionado.
        - "Crear cuenta": formulario de registro con validación de contraseñas.
    Al autenticarse exitosamente, se guardan en session_state:
        user_email, user_name, user_role, auth_method, authenticated=True.
    POSIBLE ERROR: La clave SUPABASE_KEY parece ser una clave pública (publishable),
        que podría no tener permisos para leer la tabla 'usuarios' según las
        políticas RLS (Row Level Security) configuradas en Supabase.
    """
    if st.session_state.get("authenticated"):
        return

    st.markdown("<div style='height:5vh'></div>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown("""
        <div style="display:flex;align-items:center;gap:16px;margin-bottom:28px;">
            <div style="width:48px;height:48px;background:linear-gradient(135deg,#1c2a3a,#243447);
                border:1px solid rgba(255,255,255,0.12);border-radius:10px;
                display:flex;align-items:center;justify-content:center;
                font-size:24px;box-shadow:0 4px 20px rgba(0,0,0,0.5);flex-shrink:0;">🏭</div>
            <div>
                <div style="font-family:'Syne','Inter','Segoe UI',Arial,sans-serif;
                    font-size:32px;font-weight:900;color:#f0f4ff;letter-spacing:-0.8px;
                    line-height:1.1;text-shadow:0 2px 12px rgba(0,0,0,0.4);">InvenTech Pro</div>
                <div style="font-size:11px;color:#8893b0;letter-spacing:1.5px;
                    text-transform:uppercase;margin-top:4px;">
                    Control de Inventario · Metalmecánica</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style="font-size:11px;font-weight:600;color:#6b7a99;
            text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">
            Método de acceso</div>
        """, unsafe_allow_html=True)

        method = st.radio(
            "método",
            ["👤 Usuario del sistema", "🔐 Cuenta Supabase"],
            horizontal=True,
            label_visibility="hidden",
            key="login_method_radio",
        )
        is_system = "Usuario" in method
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        tab_sign, tab_reg = st.tabs(["  Iniciar sesión  ", "  Crear cuenta  "])

        with tab_sign:
            if is_system:
                with st.form("form_signin_system", clear_on_submit=False):
                    st.markdown("""
                    <div style="font-family:'Syne',sans-serif;font-size:16px;
                        font-weight:700;color:#f0f4ff;margin-bottom:3px;">Bienvenido de vuelta</div>
                    <div style="font-size:12.5px;color:#8893b0;margin-bottom:18px;">
                        Ingresa tus credenciales del sistema</div>
                    """, unsafe_allow_html=True)
                    username  = st.text_input("Usuario", placeholder="ej: jperez", key="si_sys_user")
                    password  = st.text_input("Contraseña", type="password", placeholder="••••••••", key="si_sys_pass")
                    submitted = st.form_submit_button("Iniciar sesión →", use_container_width=True, type="primary")
                if submitted:
                    st.session_state.login_error  = ""
                    st.session_state.login_success = ""
                    if not username or not password:
                        st.session_state.login_error = "Completa todos los campos."
                    else:
                        try:
                            ph  = hash_password(password)
                            res = supabase.table("usuarios").select("*").eq("username", username).eq("password_hash", ph).execute()
                            if res.data:
                                u = res.data[0]
                                st.session_state.authenticated = True
                                st.session_state.user_email    = u.get("email", username)
                                st.session_state.user_name     = u.get("nombre_completo", username)
                                st.session_state.user_role     = u.get("rol", "Operador")
                                st.session_state.auth_method   = "custom_user"
                                supabase.table("usuarios").update({"ultimo_acceso": datetime.utcnow().isoformat()}).eq("username", username).execute()
                                st.rerun()
                                st.stop()
                            else:
                                st.session_state.login_error = "Usuario o contraseña incorrectos."
                        except Exception as e:
                            st.session_state.login_error = f"Error de conexión: {str(e)[:100]}"
            else:
                with st.form("form_signin_supabase", clear_on_submit=False):
                    st.markdown("""
                    <div style="font-family:'Syne',sans-serif;font-size:16px;
                        font-weight:700;color:#f0f4ff;margin-bottom:3px;">Acceso con cuenta Supabase</div>
                    <div style="font-size:12.5px;color:#8893b0;margin-bottom:18px;">
                        Usa tu correo y contraseña de Supabase Auth</div>
                    """, unsafe_allow_html=True)
                    email     = st.text_input("Correo electrónico", placeholder="usuario@empresa.com", key="si_sb_email")
                    password  = st.text_input("Contraseña", type="password", placeholder="••••••••", key="si_sb_pass")
                    submitted = st.form_submit_button("Iniciar sesión →", use_container_width=True, type="primary")
                if submitted:
                    st.session_state.login_error  = ""
                    st.session_state.login_success = ""
                    if not email or not password:
                        st.session_state.login_error = "Completa todos los campos."
                    else:
                        try:
                            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                            if res.user:
                                st.session_state.authenticated = True
                                st.session_state.user_email    = res.user.email
                                st.session_state.user_name     = res.user.email.split("@")[0].title()
                                st.session_state.user_role     = "Admin"
                                st.session_state.auth_method   = "supabase_auth"
                                st.rerun()
                                st.stop()
                            else:
                                st.session_state.login_error = "Credenciales incorrectas."
                        except Exception:
                            st.session_state.login_error = "Credenciales incorrectas."

        with tab_reg:
            if is_system:
                with st.form("form_register_system", clear_on_submit=True):
                    st.markdown("""
                    <div style="font-family:'Syne',sans-serif;font-size:16px;
                        font-weight:700;color:#f0f4ff;margin-bottom:3px;">Crear cuenta del sistema</div>
                    <div style="font-size:12.5px;color:#8893b0;margin-bottom:18px;">
                        El rol asignado será <strong style="color:#3ecf8e;">Operador</strong> por defecto</div>
                    """, unsafe_allow_html=True)
                    full_name    = st.text_input("Nombre completo", placeholder="Juan Pérez", key="reg_sys_name")
                    username     = st.text_input("Nombre de usuario", placeholder="ej: jperez", key="reg_sys_user")
                    password     = st.text_input("Contraseña", type="password", placeholder="Mínimo 6 caracteres", key="reg_sys_pass")
                    password2    = st.text_input("Confirmar contraseña", type="password", placeholder="••••••••", key="reg_sys_pass2")
                    submitted_reg = st.form_submit_button("Crear cuenta →", use_container_width=True, type="primary")
                if submitted_reg:
                    st.session_state.login_error  = ""
                    st.session_state.login_success = ""
                    if not full_name or not username or not password:
                        st.session_state.login_error = "Nombre, usuario y contraseña son obligatorios."
                    elif len(password) < 6:
                        st.session_state.login_error = "La contraseña debe tener al menos 6 caracteres."
                    elif password != password2:
                        st.session_state.login_error = "Las contraseñas no coinciden."
                    else:
                        try:
                            exists = supabase.table("usuarios").select("id").eq("username", username).execute()
                            if exists.data:
                                st.session_state.login_error = "Ese nombre de usuario ya está en uso."
                            else:
                                supabase.table("usuarios").insert({
                                    "username": username, "password_hash": hash_password(password),
                                    "nombre_completo": full_name, "email": None,
                                    "rol": "Operador", "fecha_registro": datetime.utcnow().isoformat(),
                                }).execute()
                                st.session_state.login_success = f"✓ Cuenta '{username}' creada. Ya puedes iniciar sesión."
                        except Exception as e:
                            st.session_state.login_error = f"Error al registrar: {str(e)[:100]}"
            else:
                with st.form("form_register_supabase", clear_on_submit=True):
                    st.markdown("""
                    <div style="font-family:'Syne',sans-serif;font-size:16px;
                        font-weight:700;color:#f0f4ff;margin-bottom:3px;">Crear cuenta Supabase</div>
                    <div style="font-size:12.5px;color:#8893b0;margin-bottom:18px;">
                        Recibirás un correo de confirmación</div>
                    """, unsafe_allow_html=True)
                    email        = st.text_input("Correo electrónico", placeholder="usuario@empresa.com", key="reg_sb_email")
                    password     = st.text_input("Contraseña", type="password", placeholder="Mínimo 6 caracteres", key="reg_sb_pass")
                    password2    = st.text_input("Confirmar contraseña", type="password", placeholder="••••••••", key="reg_sb_pass2")
                    submitted_reg = st.form_submit_button("Crear cuenta →", use_container_width=True, type="primary")
                if submitted_reg:
                    st.session_state.login_error  = ""
                    st.session_state.login_success = ""
                    if not email or not password:
                        st.session_state.login_error = "Completa todos los campos."
                    elif len(password) < 6:
                        st.session_state.login_error = "La contraseña debe tener al menos 6 caracteres."
                    elif password != password2:
                        st.session_state.login_error = "Las contraseñas no coinciden."
                    else:
                        try:
                            res = supabase.auth.sign_up({"email": email, "password": password})
                            if res.user:
                                st.session_state.login_success = "✓ Cuenta creada. Revisa tu correo para confirmar."
                            else:
                                st.session_state.login_error = "No se pudo crear la cuenta."
                        except Exception as e:
                            st.session_state.login_error = f"Error: {str(e)[:100]}"

        if st.session_state.login_error:
            st.error(st.session_state.login_error)
        if st.session_state.login_success:
            st.success(st.session_state.login_success)

        st.markdown("""
        <div style="margin-top:24px;padding-top:16px;
            border-top:1px solid rgba(255,255,255,0.06);
            text-align:center;font-size:11px;color:#3a4560;letter-spacing:0.5px;">
            InvenTech Pro · Sistema de inventario metalmecánica · v1.0
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:5vh'></div>", unsafe_allow_html=True)


# =============================================================================
# SECCIÓN 10: BARRA LATERAL (Sidebar de navegación)
# =============================================================================

def render_sidebar():
    """
    Renderiza el sidebar con la marca, datos del usuario y menú de navegación.
    Componentes:
        - Logo e ícono de la marca "InvenTech Pro".
        - Bloque con las iniciales, nombre, email y rol del usuario activo.
        - Menú de navegación tipo radio (sin bolitas visibles, estilo sidebar).
        - Botón de 'Cerrar sesión' que limpia el session_state y recarga.
    Retorna: el ítem del menú seleccionado (string), que el router usa para
        decidir qué función de página renderizar.
    """
    with st.sidebar:
        name     = st.session_state.get("user_name", "Usuario")
        email    = st.session_state.get("user_email", "")
        role     = st.session_state.get("user_role", "Operador")
        raw      = name.split("@")[0] if "@" in name else name
        parts    = [p for p in raw.split() if p.isalpha()]
        initials = "".join([p[0].upper() for p in parts[:2]]) if parts else raw[0].upper() if raw else "U"

        st.markdown(f"""
        <div class="sidebar-brand">
            <div class="sidebar-brand-icon">⚙</div>
            <div>
                <div class="sidebar-brand-name">InvenTech Pro</div>
                <div class="sidebar-brand-sub">Metalmecánica</div>
            </div>
        </div>
        <div class="sidebar-user-block">
            <div class="sidebar-avatar">{initials}</div>
            <div style="min-width:0;">
                <div class="sidebar-user-name">{name}</div>
                <div class="sidebar-user-email">{email}</div>
                <div class="sidebar-role-badge">{role}</div>
            </div>
        </div>
        <div class="sidebar-nav-label">Navegación</div>
        <div class="sidebar-nav-wrap">
        """, unsafe_allow_html=True)

        menu = st.radio("", [
            "📊  Dashboard",
            "📦  Productos",
            "🏷️  Categorías",
            "🏭  Proveedores",
            "🛒  Órdenes de Compra",
            "🔄  Operaciones Almacén",
            "📋  Movimientos",
        ], label_visibility="collapsed")

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("---")
        if st.button("Cerrar sesión", use_container_width=True):
            for key in ["authenticated","user_email","user_name","user_role",
                        "auth_method","chat_history","login_error","login_success"]:
                st.session_state.pop(key, None)
            st.rerun()

    return menu


# =============================================================================
# SECCIÓN 11: COMPONENTE REUTILIZABLE — ENCABEZADO DE PÁGINA
# =============================================================================

def render_header(title: str, subtitle: str = ""):
    """
    Renderiza el encabezado estándar de cada sección con título y subtítulo.
    Usa una línea divisoria inferior para separar visualmente el header del
    contenido. Se usa en todas las páginas para mantener consistencia visual.
    """
    sub_html = f'<div class="page-subtitle">{subtitle}</div>' if subtitle else ""
    st.markdown(f"""
    <div class="page-header">
        <div>
            <div class="page-title">{title}</div>
            {sub_html}
        </div>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# SECCIÓN 12: PÁGINA — DASHBOARD (Panel de Control)
# =============================================================================

def render_dashboard():
    """
    Renderiza la página principal de resumen ejecutivo del almacén.
    Componentes:
        - 4 tarjetas KPI con: total de productos, productos bajo stock mínimo,
          órdenes de compra pendientes y total de movimientos registrados.
        - Columna izquierda: lista de alertas de productos en stock crítico.
        - Columna derecha: tabla con los últimos 8 movimientos del almacén.
        - Gráfico de barras agrupadas (Plotly): stock actual vs. stock mínimo
          por cada producto, con tema oscuro personalizado.
    Todos los datos se obtienen en tiempo real desde Supabase al cargar la página.
    """
    render_header("Panel de control", "Resumen en tiempo real del almacén")
    productos  = fetch("producto")
    ordenes    = fetch("orden_compra")
    movs       = fetch("movimiento")
    total_prod = len(productos)
    bajo_stock = len(productos[productos["stock_actual"] <= productos["stock_minimo"]]) if not productos.empty else 0
    ord_pend   = len(ordenes[ordenes["estado"] == "pendiente"]) if not ordenes.empty else 0
    total_movs = len(movs)
    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card blue"><div class="kpi-icon">📦</div><div class="kpi-label">Total productos</div><div class="kpi-value">{total_prod}</div><div class="kpi-accent"></div></div>
        <div class="kpi-card red"><div class="kpi-icon">⚠️</div><div class="kpi-label">Bajo stock mínimo</div><div class="kpi-value">{bajo_stock}</div><div class="kpi-accent"></div></div>
        <div class="kpi-card yellow"><div class="kpi-icon">🛒</div><div class="kpi-label">Órdenes pendientes</div><div class="kpi-value">{ord_pend}</div><div class="kpi-accent"></div></div>
        <div class="kpi-card green"><div class="kpi-icon">🔄</div><div class="kpi-label">Movimientos totales</div><div class="kpi-value">{total_movs}</div><div class="kpi-accent"></div></div>
    </div>
    """, unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-label">Alertas de stock crítico</div>', unsafe_allow_html=True)
        if not productos.empty:
            criticos = productos[productos["stock_actual"] <= productos["stock_minimo"]]
            if not criticos.empty:
                for _, r in criticos.iterrows():
                    st.markdown(f"""<div class="alert-row"><div class="alert-dot"></div>
                    <div class="alert-text"><b>{r['codigo']}</b> — {r['nombre']}</div>
                    <div class="alert-badge">{r['stock_actual']} {r['unidad']}</div></div>""",
                    unsafe_allow_html=True)
            else:
                st.success("Todos los productos tienen stock suficiente.")
        else:
            empty_state("📦", "Sin productos registrados", "Agrega productos desde la sección Productos")
    with col2:
        st.markdown('<div class="section-label">Últimos movimientos</div>', unsafe_allow_html=True)
        if not movs.empty:
            ultimos = movs.sort_values("fecha", ascending=False).head(8)[["fecha","tipo","cantidad","saldo"]]
            ultimos["fecha"] = pd.to_datetime(ultimos["fecha"]).dt.strftime("%d/%m %H:%M")
            st.dataframe(ultimos.rename(columns={"fecha":"Fecha","tipo":"Tipo","cantidad":"Cantidad","saldo":"Saldo"}),
                         use_container_width=True, hide_index=True)
        else:
            empty_state("🔄", "Sin movimientos registrados", "Los movimientos se generan al registrar operaciones")
    st.markdown('<div class="section-label">Stock por producto</div>', unsafe_allow_html=True)
    if not productos.empty:
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Stock actual", x=productos["nombre"], y=productos["stock_actual"], marker_color="#3ecf8e"))
        fig.add_trace(go.Bar(name="Stock mínimo", x=productos["nombre"], y=productos["stock_minimo"],
                             marker_color="#2a2a2a", marker_line_color="#3e3e3e", marker_line_width=1))
        fig.update_layout(
            barmode="group",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#a0a0a0", family="Inter"),
            legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#2e2e2e", borderwidth=1),
            xaxis=dict(gridcolor="#1e1e1e", linecolor="#2e2e2e"),
            yaxis=dict(gridcolor="#1e1e1e", linecolor="#2e2e2e"),
            margin=dict(l=0, r=0, t=10, b=0),
            height=240,
        )
        st.plotly_chart(fig, use_container_width=True)


# =============================================================================
# SECCIÓN 13: PÁGINA — PRODUCTOS
# =============================================================================

def render_productos():
    """
    Renderiza la página de gestión de productos del inventario.
    Pestañas:
        A) Listado:
            - Búsqueda por código o nombre con filtro en tiempo real.
            - Tabla con columnas: código, nombre, unidad, categoría,
              stock actual, stock mínimo y precio unitario.
            - Advertencia si hay productos bajo el stock mínimo.
            - Selector para editar (expander con formulario) o eliminar.
            - Eliminación en cascada: borra detalles de orden, detalles de
              operación y movimientos asociados antes de borrar el producto.
        B) Agregar producto:
            - Formulario con campos: código, nombre, unidad, categoría,
              stock inicial, stock mínimo y precio unitario.
            - Registro de auditoría al agregar.
    """
    render_header("Productos", "Gestión de materiales, insumos y repuestos")
    tabs = st.tabs(["Listado", "Agregar producto"])
    with tabs[0]:
        df = fetch("producto", "*, categoria(nombre)")
        if df.empty:
            empty_state("📦", "Sin productos registrados", "Agrega uno desde la pestaña 'Agregar producto'")
        else:
            if "categoria" in df.columns:
                df["categoria_nombre"] = df["categoria"].apply(lambda x: x["nombre"] if isinstance(x, dict) else "—")
            cols_show = [c for c in ["codigo","nombre","unidad","categoria_nombre","stock_actual","stock_minimo","precio_unitario"] if c in df.columns]
            search = st.text_input("Buscar por código o nombre", "", placeholder="Ej: MP-001 o Acero...")
            vista  = df.copy()
            if search:
                mask  = (vista["codigo"].str.contains(search, case=False, na=False) |
                         vista["nombre"].str.contains(search, case=False, na=False))
                vista = vista[mask]
            low = vista[vista["stock_actual"] <= vista["stock_minimo"]]
            if not low.empty:
                st.warning(f"{len(low)} producto(s) con stock por debajo del mínimo.")
            st.dataframe(vista[cols_show].rename(columns={
                "codigo":"Código","nombre":"Nombre","unidad":"Unidad",
                "categoria_nombre":"Categoría","stock_actual":"Stock actual",
                "stock_minimo":"Stock mínimo","precio_unitario":"Precio (S/)"}),
                use_container_width=True, hide_index=True)
            st.markdown('<div class="section-label">Editar o eliminar</div>', unsafe_allow_html=True)
            opciones = {f"{r['codigo']} — {r['nombre']}": r["id"] for _, r in df.iterrows()}
            sel = st.selectbox("Seleccionar producto", list(opciones.keys()))
            if sel:
                pid = opciones[sel]
                row = df[df["id"] == pid].iloc[0]
                with st.expander("Editar producto", expanded=False):
                    cats      = fetch("categoria")
                    cat_map   = {r["nombre"]: r["id"] for _, r in cats.iterrows()} if not cats.empty else {}
                    cat_names = list(cat_map.keys())
                    with st.form(f"edit_prod_{pid}"):
                        c1, c2    = st.columns(2)
                        codigo    = c1.text_input("Código", value=row.get("codigo",""))
                        nombre    = c2.text_input("Nombre", value=row.get("nombre",""))
                        unidad    = c1.selectbox("Unidad", ["kg","unidad","m","lt"],
                            index=["kg","unidad","m","lt"].index(row.get("unidad","unidad"))
                            if row.get("unidad") in ["kg","unidad","m","lt"] else 0)
                        cat_actual = row.get("categoria_nombre", cat_names[0] if cat_names else "")
                        cat_sel    = c2.selectbox("Categoría", cat_names,
                            index=cat_names.index(cat_actual) if cat_actual in cat_names else 0)
                        stock_act = c1.number_input("Stock actual", value=float(row.get("stock_actual",0)), min_value=0.0)
                        stock_min = c2.number_input("Stock mínimo", value=float(row.get("stock_minimo",0)), min_value=0.0)
                        precio    = st.number_input("Precio unitario (S/)", value=float(row.get("precio_unitario",0)), min_value=0.0)
                        if st.form_submit_button("Guardar cambios", type="primary"):
                            try:
                                update("producto", pid, {"codigo": codigo, "nombre": nombre, "unidad": unidad,
                                    "id_categoria": cat_map.get(cat_sel),
                                    "stock_actual": stock_act, "stock_minimo": stock_min, "precio_unitario": precio})
                                log_auditoria("EDITAR", "producto", f"Editado {codigo} — {nombre}")
                                ok("Producto actualizado"); st.rerun()
                            except Exception as e: err(e)
                ckey = confirm_key("del_prod", pid)
                if st.button("Eliminar producto", key=f"del_prod_{pid}"):
                    st.session_state[ckey] = True
                if st.session_state.get(ckey):
                    st.warning("¿Confirmar eliminación?")
                    ca, cb = st.columns(2)
                    if ca.button("Sí, eliminar", key=f"confirm_yes_{pid}"):
                        try:
                            supabase.table("detalle_orden").delete().eq("id_producto", pid).execute()
                            supabase.table("detalle_operacion").delete().eq("id_producto", pid).execute()
                            supabase.table("movimiento").delete().eq("id_producto", pid).execute()
                            log_auditoria("ELIMINAR", "producto", f"Eliminado id={pid}")
                            delete("producto", pid)
                            ok("Producto eliminado")
                            st.session_state.pop(ckey, None)
                            st.rerun()
                        except Exception as e:
                            err(e)
                    if cb.button("Cancelar", key=f"confirm_no_{pid}"):
                        st.session_state.pop(ckey, None)
                        st.rerun()
    with tabs[1]:
        cats     = fetch("categoria")
        cat_map2 = {r["nombre"]: r["id"] for _, r in cats.iterrows()} if not cats.empty else {}
        with st.form("add_producto"):
            c1, c2    = st.columns(2)
            codigo    = c1.text_input("Código único (ej: MP-001)*")
            nombre    = c2.text_input("Nombre / descripción*")
            unidad    = c1.selectbox("Unidad de medida", ["kg","unidad","m","lt"])
            cat_sel   = c2.selectbox("Categoría", list(cat_map2.keys()) or ["Sin categorías"])
            stock_act = c1.number_input("Stock inicial", min_value=0.0, value=0.0)
            stock_min = c2.number_input("Stock mínimo",  min_value=0.0, value=0.0)
            precio    = st.number_input("Precio unitario (S/)", min_value=0.0, value=0.0)
            if st.form_submit_button("Agregar producto", type="primary"):
                if not codigo or not nombre:
                    st.error("Código y nombre son obligatorios.")
                else:
                    try:
                        insert("producto", {"codigo": codigo, "nombre": nombre, "unidad": unidad,
                            "id_categoria": cat_map2.get(cat_sel),
                            "stock_actual": stock_act, "stock_minimo": stock_min, "precio_unitario": precio})
                        log_auditoria("AGREGAR", "producto", f"Nuevo producto {codigo} — {nombre}")
                        ok("Producto agregado"); st.rerun()
                    except Exception as e: err(e)


# =============================================================================
# SECCIÓN 14: PÁGINA — CATEGORÍAS
# =============================================================================

def render_categorias():
    """
    Renderiza la página de gestión de categorías de productos.
    Pestañas:
        A) Listado:
            - Tabla simple con los nombres de categorías existentes.
            - Selector para editar nombre (expander con formulario).
            - Eliminación en cascada: primero borra los movimientos, detalles
              de operación y detalles de orden de todos los productos de esa
              categoría, luego los productos y finalmente la categoría.
        B) Nueva categoría:
            - Formulario con un solo campo: nombre de la categoría.
    """
    render_header("Categorías", "Clasifica los materiales del inventario")
    tabs = st.tabs(["Listado", "Nueva categoría"])
    with tabs[0]:
        df = fetch("categoria")
        if df.empty:
            empty_state("🏷️", "Sin categorías registradas", "Agrega una desde la pestaña 'Nueva categoría'")
        else:
            st.dataframe(df[["nombre"]].rename(columns={"nombre":"Nombre"}),
                         use_container_width=True, hide_index=True)
            st.markdown('<div class="section-label">Editar o eliminar</div>', unsafe_allow_html=True)
            opciones = {r["nombre"]: r["id"] for _, r in df.iterrows()}
            sel = st.selectbox("Seleccionar categoría", list(opciones.keys()))
            if sel:
                cid = opciones[sel]
                with st.expander("Editar categoría", expanded=False):
                    with st.form(f"edit_cat_{cid}"):
                        nuevo = st.text_input("Nombre", value=sel)
                        if st.form_submit_button("Guardar cambios", type="primary"):
                            try:
                                update("categoria", cid, {"nombre": nuevo})
                                log_auditoria("EDITAR", "categoria", f"Renombrada a {nuevo}")
                                ok("Categoría actualizada"); st.rerun()
                            except Exception as e: err(e)
                ckey = confirm_key("del_cat", cid)
                if st.button("Eliminar categoría", key=f"dcat_{cid}"):
                    st.session_state[ckey] = True
                if st.session_state.get(ckey):
                    st.warning("¿Confirmar eliminación?")
                    ca, cb = st.columns(2)
                    if ca.button("Sí, eliminar", key=f"catsy_{cid}"):
                        try:
                            prods_cat = supabase.table("producto").select("id").eq("id_categoria", cid).execute()
                            for p in (prods_cat.data or []):
                                pid_c = p["id"]
                                supabase.table("detalle_orden").delete().eq("id_producto", pid_c).execute()
                                supabase.table("detalle_operacion").delete().eq("id_producto", pid_c).execute()
                                supabase.table("movimiento").delete().eq("id_producto", pid_c).execute()
                            supabase.table("producto").delete().eq("id_categoria", cid).execute()
                            delete("categoria", cid)
                            log_auditoria("ELIMINAR", "categoria", f"Eliminada id={cid}")
                            ok("Categoría eliminada")
                            st.session_state.pop(ckey, None)
                            st.rerun()
                        except Exception as e:
                            err(e)
                    if cb.button("Cancelar", key=f"catno_{cid}"):
                        st.session_state.pop(ckey, None)
                        st.rerun()
    with tabs[1]:
        with st.form("add_cat"):
            nombre = st.text_input("Nombre de la categoría*")
            if st.form_submit_button("Agregar categoría", type="primary"):
                if not nombre:
                    st.error("El nombre es obligatorio.")
                else:
                    try:
                        insert("categoria", {"nombre": nombre})
                        log_auditoria("AGREGAR", "categoria", f"Nueva: {nombre}")
                        ok("Categoría creada"); st.rerun()
                    except Exception as e: err(e)


# =============================================================================
# SECCIÓN 15: PÁGINA — PROVEEDORES
# =============================================================================

def render_proveedores():
    """
    Renderiza la página de gestión de proveedores del sistema.
    Pestañas:
        A) Listado:
            - Tabla con nombre, RUC y teléfono de cada proveedor.
            - Edición de datos (nombre, RUC, teléfono) con formulario en expander.
            - Eliminación en cascada:
                1. Borra detalles de cada orden de compra del proveedor.
                2. Borra todas las órdenes de compra del proveedor.
                3. Desvincula las operaciones de almacén (pone NULL en id_proveedor).
                4. Elimina el proveedor.
        B) Nuevo proveedor:
            - Formulario con nombre (obligatorio), RUC y teléfono (opcionales).
    """
    render_header("Proveedores", "Empresas y personas que abastecen la planta")
    tabs = st.tabs(["Listado", "Nuevo proveedor"])
    with tabs[0]:
        df = fetch("proveedor")
        if df.empty:
            empty_state("🏭", "Sin proveedores registrados", "Agrega uno desde la pestaña 'Nuevo proveedor'")
        else:
            cols = [c for c in ["nombre","ruc","telefono"] if c in df.columns]
            st.dataframe(df[cols].rename(columns={"nombre":"Nombre","ruc":"RUC","telefono":"Teléfono"}),
                         use_container_width=True, hide_index=True)
            st.markdown('<div class="section-label">Editar o eliminar</div>', unsafe_allow_html=True)
            opciones = {r["nombre"]: r["id"] for _, r in df.iterrows()}
            sel = st.selectbox("Seleccionar proveedor", list(opciones.keys()))
            if sel:
                pid = opciones[sel]
                row = df[df["id"] == pid].iloc[0]
                with st.expander("Editar proveedor", expanded=False):
                    with st.form(f"edit_prov_{pid}"):
                        c1, c2 = st.columns(2)
                        nombre = c1.text_input("Nombre / Razón social", value=row.get("nombre",""))
                        ruc    = c2.text_input("RUC", value=row.get("ruc","") or "")
                        tel    = c1.text_input("Teléfono", value=row.get("telefono","") or "")
                        if st.form_submit_button("Guardar cambios", type="primary"):
                            try:
                                update("proveedor", pid, {"nombre": nombre, "ruc": ruc or None, "telefono": tel or None})
                                log_auditoria("EDITAR", "proveedor", f"Editado: {nombre}")
                                ok("Proveedor actualizado"); st.rerun()
                            except Exception as e: err(e)
                ckey = confirm_key("del_prov", pid)
                if st.button("Eliminar proveedor", key=f"dprov_{pid}"):
                    st.session_state[ckey] = True
                if st.session_state.get(ckey):
                    st.warning("¿Confirmar eliminación?")
                    ca, cb = st.columns(2)
                    if ca.button("Sí, eliminar", key=f"provsiy_{pid}"):
                        try:
                            ords = supabase.table("orden_compra").select("id").eq("id_proveedor", pid).execute()
                            for o in (ords.data or []):
                                supabase.table("detalle_orden").delete().eq("id_orden", o["id"]).execute()
                            supabase.table("orden_compra").delete().eq("id_proveedor", pid).execute()
                            supabase.table("operacion_almacen").update({"id_proveedor": None}).eq("id_proveedor", pid).execute()
                            delete("proveedor", pid)
                            log_auditoria("ELIMINAR", "proveedor", f"Eliminado id={pid}")
                            ok("Proveedor eliminado")
                            st.session_state.pop(ckey, None)
                            st.rerun()
                        except Exception as e:
                            err(e)
                    if cb.button("Cancelar", key=f"provnon_{pid}"):
                        st.session_state.pop(ckey, None)
                        st.rerun()
    with tabs[1]:
        with st.form("add_prov"):
            c1, c2 = st.columns(2)
            nombre = c1.text_input("Nombre / Razón social*")
            ruc    = c2.text_input("RUC (opcional)")
            tel    = c1.text_input("Teléfono (opcional)")
            if st.form_submit_button("Agregar proveedor", type="primary"):
                if not nombre:
                    st.error("El nombre es obligatorio.")
                else:
                    try:
                        insert("proveedor", {"nombre": nombre, "ruc": ruc or None, "telefono": tel or None})
                        log_auditoria("AGREGAR", "proveedor", f"Nuevo: {nombre}")
                        ok("Proveedor agregado"); st.rerun()
                    except Exception as e: err(e)


# =============================================================================
# SECCIÓN 16: PÁGINA — ÓRDENES DE COMPRA
# =============================================================================

def render_ordenes():
    """
    Renderiza la página de gestión de órdenes de compra a proveedores.
    Pestañas:
        A) Listado:
            - Tabla con número de orden, proveedor, fecha y estado.
            - Selector para cambiar el estado (pendiente / recibida / cancelada).
            - Eliminación de la orden con borrado previo de sus detalles.
        B) Nueva orden:
            - Formulario con número de orden, proveedor, fecha y estado inicial.
            - Sección dinámica para agregar N productos con cantidad y precio.
            - Al guardar: crea la orden y luego inserta cada detalle_orden
              con su subtotal calculado (cantidad × precio).
        C) Ver detalle:
            - Selector de orden existente.
            - Tabla con código, nombre del producto, cantidad, precio y subtotal
              de cada ítem de esa orden.
    """
    render_header("Órdenes de Compra", "Documentos formales de compra a proveedores")
    tabs = st.tabs(["Listado", "Nueva orden", "Ver detalle"])
    with tabs[0]:
        df = fetch("orden_compra", "*, proveedor(nombre)")
        if df.empty:
            empty_state("🛒", "Sin órdenes de compra", "Crea una desde la pestaña 'Nueva orden'")
        else:
            if "proveedor" in df.columns:
                df["proveedor_nombre"] = df["proveedor"].apply(lambda x: x["nombre"] if isinstance(x, dict) else "—")
            cols = [c for c in ["numero","proveedor_nombre","fecha","estado"] if c in df.columns]
            st.dataframe(df[cols].rename(columns={"numero":"N° Orden","proveedor_nombre":"Proveedor","fecha":"Fecha","estado":"Estado"}),
                         use_container_width=True, hide_index=True)
            st.markdown('<div class="section-label">Editar estado</div>', unsafe_allow_html=True)
            opciones = {r["numero"]: r["id"] for _, r in df.iterrows()}
            sel = st.selectbox("Seleccionar orden", list(opciones.keys()), key="sel_orden_listado")
            if sel:
                oid = opciones[sel]
                row = df[df["id"] == oid].iloc[0]
                with st.expander("Cambiar estado", expanded=False):
                    with st.form(f"edit_ord_{oid}"):
                        estados      = ["pendiente","recibida","cancelada"]
                        est_idx      = estados.index(row.get("estado","pendiente")) if row.get("estado") in estados else 0
                        nuevo_estado = st.selectbox("Estado", estados, index=est_idx)
                        if st.form_submit_button("Guardar cambios", type="primary"):
                            try:
                                update("orden_compra", oid, {"estado": nuevo_estado})
                                log_auditoria("EDITAR", "orden_compra", f"Orden {sel} → {nuevo_estado}")
                                ok("Estado actualizado"); st.rerun()
                            except Exception as e: err(e)
                ckey = confirm_key("del_ord", oid)
                if st.button("Eliminar orden", key=f"dord_{oid}"):
                    st.session_state[ckey] = True
                if st.session_state.get(ckey):
                    st.warning("¿Confirmar eliminación?")
                    ca, cb = st.columns(2)
                    if ca.button("Sí, eliminar", key=f"ordsy_{oid}"):
                        try:
                            supabase.table("detalle_orden").delete().eq("id_orden", oid).execute()
                            delete("orden_compra", oid)
                            log_auditoria("ELIMINAR", "orden_compra", f"Eliminada orden {sel}")
                            ok("Orden eliminada")
                            st.session_state.pop(ckey, None)
                            st.rerun()
                        except Exception as e:
                            err(e)
                    if cb.button("Cancelar", key=f"ordn_{oid}"):
                        st.session_state.pop(ckey, None)
                        st.rerun()
    with tabs[1]:
        provs    = fetch("proveedor")
        prov_map = {r["nombre"]: r["id"] for _, r in provs.iterrows()} if not provs.empty else {}
        prods    = fetch("producto")
        prod_map = {f"{r['codigo']} — {r['nombre']}": r["id"] for _, r in prods.iterrows()} if not prods.empty else {}
        with st.form("add_orden"):
            c1, c2    = st.columns(2)
            numero    = c1.text_input("N° de orden (ej: OC-2024-001)*")
            prov_sel  = c2.selectbox("Proveedor*", list(prov_map.keys()) or ["Sin proveedores"])
            fecha_ord = c1.date_input("Fecha", value=date.today())
            estado    = c2.selectbox("Estado", ["pendiente","recibida","cancelada"])
            st.markdown('<div class="section-label">Productos de la orden (al menos 1)</div>', unsafe_allow_html=True)
            n_items = st.number_input("Cantidad de ítems", min_value=1, max_value=20, value=1, step=1)
            items = []
            for i in range(int(n_items)):
                ic1, ic2, ic3 = st.columns(3)
                prod = ic1.selectbox(f"Producto {i+1}", list(prod_map.keys()), key=f"op_{i}")
                cant = ic2.number_input(f"Cantidad {i+1}", min_value=0.01, value=1.0, key=f"oq_{i}")
                prec = ic3.number_input(f"Precio unit. {i+1} (S/)", min_value=0.0, value=0.0, key=f"opr_{i}")
                items.append((prod, cant, prec))
            if st.form_submit_button("Crear orden de compra", type="primary"):
                if not numero or not prov_map:
                    st.error("Número de orden y proveedor son obligatorios.")
                else:
                    try:
                        ord_res = insert("orden_compra", {"numero": numero,
                            "id_proveedor": prov_map[prov_sel], "fecha": str(fecha_ord), "estado": estado})
                        ord_id = ord_res.data[0]["id"]
                        for prod_lbl, cant, prec in items:
                            insert("detalle_orden", {"id_orden": ord_id, "id_producto": prod_map[prod_lbl],
                                "cantidad": cant, "precio_unitario": prec, "subtotal": round(cant*prec, 4)})
                        log_auditoria("AGREGAR", "orden_compra", f"Orden {numero} — {len(items)} ítem(s)")
                        ok(f"Orden {numero} creada con {len(items)} ítem(s)"); st.rerun()
                    except Exception as e: err(e)
    with tabs[2]:
        df_ords = fetch("orden_compra")
        if not df_ords.empty:
            opciones = {r["numero"]: r["id"] for _, r in df_ords.iterrows()}
            sel = st.selectbox("Seleccionar orden", list(opciones.keys()), key="sel_orden_detalle")
            oid = opciones[sel]
            det = supabase.table("detalle_orden").select("*, producto(codigo,nombre)").eq("id_orden", oid).execute()
            if det.data:
                rows = []
                for d in det.data:
                    p = d.get("producto", {})
                    rows.append({"Código": p.get("codigo",""), "Producto": p.get("nombre",""),
                                 "Cantidad": d["cantidad"], "Precio unit.": d["precio_unitario"], "Subtotal": d["subtotal"]})
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                empty_state("📋", "Sin ítems en esta orden", "")
        else:
            empty_state("🛒", "Sin órdenes registradas", "")


# =============================================================================
# SECCIÓN 17: PÁGINA — OPERACIONES DE ALMACÉN
# =============================================================================

def render_operaciones():
    """
    Renderiza la página de registro de entradas y salidas de materiales.
    Es la sección más crítica del sistema ya que actualiza el stock real.
    Pestañas:
        A) Listado:
            - Tabla con documento, tipo, motivo, proveedor y fecha.
            - Eliminación en cascada: borra detalles de la operación,
              los movimientos asociados y luego la operación.
            ADVERTENCIA: al eliminar una operación NO se revierte el stock.
              Esto puede generar inconsistencias en el inventario.
        B) Nueva operación:
            - Tipo: "entrada" (aumenta stock) o "salida" (disminuye stock).
            - Motivo: compra, devolución, producción o ajuste.
            - Proveedor: solo aplicable en entradas por compra.
            - Sección dinámica de N productos con cantidad y precio.
            - Al guardar:
                1. Crea el registro en operacion_almacen.
                2. Por cada producto: inserta detalle_operacion.
                3. Recalcula y actualiza stock_actual en la tabla producto.
                4. Inserta un registro en movimiento con el saldo nuevo.
        C) Ver detalle:
            - Tabla con código, nombre, cantidad, precio y subtotal
              de cada ítem de la operación seleccionada.
    """
    render_header("Operaciones de Almacén", "Registra entradas y salidas de materiales")
    tabs = st.tabs(["Listado", "Nueva operación", "Ver detalle"])
    with tabs[0]:
        df = fetch("operacion_almacen", "*, proveedor(nombre)")
        if df.empty:
            empty_state("🔄", "Sin operaciones registradas", "Registra una desde la pestaña 'Nueva operación'")
        else:
            if "proveedor" in df.columns:
                df["proveedor_nombre"] = df["proveedor"].apply(lambda x: x["nombre"] if isinstance(x, dict) else "—")
            cols = [c for c in ["numero_doc","tipo","motivo","proveedor_nombre","fecha"] if c in df.columns]
            st.dataframe(df[cols].rename(columns={"numero_doc":"Documento","tipo":"Tipo",
                "motivo":"Motivo","proveedor_nombre":"Proveedor","fecha":"Fecha"}),
                use_container_width=True, hide_index=True)
            st.markdown('<div class="section-label">Eliminar operación</div>', unsafe_allow_html=True)
            opciones = {f"{r['numero_doc']} ({r['tipo']})": r["id"] for _, r in df.iterrows()}
            sel = st.selectbox("Seleccionar operación", list(opciones.keys()), key="sel_op_listado")
            if sel:
                oid  = opciones[sel]
                ckey = confirm_key("del_op", oid)
                if st.button("Eliminar operación", key=f"dop_{oid}"):
                    st.session_state[ckey] = True
                if st.session_state.get(ckey):
                    st.warning("¿Confirmar eliminación?")
                    ca, cb = st.columns(2)
                    if ca.button("Sí, eliminar", key=f"opsy_{oid}"):
                        try:
                            supabase.table("detalle_operacion").delete().eq("id_operacion", oid).execute()
                            supabase.table("movimiento").delete().eq("id_operacion", oid).execute()
                            delete("operacion_almacen", oid)
                            log_auditoria("ELIMINAR", "operacion_almacen", f"Eliminada op id={oid}")
                            ok("Operación eliminada")
                            st.session_state.pop(ckey, None)
                            st.rerun()
                        except Exception as e:
                            err(e)
                    if cb.button("Cancelar", key=f"opn_{oid}"):
                        st.session_state.pop(ckey, None)
                        st.rerun()
    with tabs[1]:
        provs    = fetch("proveedor")
        prov_map = {r["nombre"]: r["id"] for _, r in provs.iterrows()} if not provs.empty else {}
        prods    = fetch("producto")
        prod_map = {f"{r['codigo']} — {r['nombre']}": r["id"] for _, r in prods.iterrows()} if not prods.empty else {}
        with st.form("add_op"):
            c1, c2      = st.columns(2)
            numero_doc  = c1.text_input("N° documento* (guía, vale, etc.)")
            tipo        = c2.selectbox("Tipo*", ["entrada","salida"])
            motivo      = c1.selectbox("Motivo*", ["compra","devolucion","produccion","ajuste"])
            prov_sel    = c2.selectbox("Proveedor (solo entradas por compra)", ["—"] + list(prov_map.keys()))
            observacion = st.text_area("Observación (opcional)")
            st.markdown('<div class="section-label">Productos de la operación (al menos 1)</div>', unsafe_allow_html=True)
            n_items = st.number_input("Cantidad de ítems", min_value=1, max_value=20, value=1, step=1)
            items = []
            for i in range(int(n_items)):
                ic1, ic2, ic3 = st.columns(3)
                prod = ic1.selectbox(f"Producto {i+1}", list(prod_map.keys()), key=f"pp_{i}")
                cant = ic2.number_input(f"Cantidad {i+1}", min_value=0.01, value=1.0, key=f"pq_{i}")
                prec = ic3.number_input(f"Precio unit. {i+1} (S/)", min_value=0.0, value=0.0, key=f"ppr_{i}")
                items.append((prod, cant, prec))
            if st.form_submit_button("Registrar operación", type="primary"):
                if not numero_doc:
                    st.error("El número de documento es obligatorio.")
                else:
                    try:
                        prov_id = prov_map.get(prov_sel) if prov_sel != "—" else None
                        op_res  = insert("operacion_almacen", {"numero_doc": numero_doc, "tipo": tipo,
                            "motivo": motivo, "id_proveedor": prov_id, "observacion": observacion or None})
                        op_id = op_res.data[0]["id"]
                        for prod_lbl, cant, prec in items:
                            prod_id = prod_map[prod_lbl]
                            insert("detalle_operacion", {"id_operacion": op_id, "id_producto": prod_id,
                                "cantidad": cant, "precio_unitario": prec, "subtotal": round(cant*prec, 4)})
                            prod_row    = supabase.table("producto").select("stock_actual").eq("id", prod_id).execute().data[0]
                            stock_prev  = prod_row["stock_actual"]
                            nuevo_stock = stock_prev + cant if tipo == "entrada" else stock_prev - cant
                            update("producto", prod_id, {"stock_actual": nuevo_stock})
                            insert("movimiento", {"id_producto": prod_id, "id_operacion": op_id,
                                "tipo": tipo, "cantidad": cant, "saldo": nuevo_stock})
                        log_auditoria("AGREGAR", "operacion_almacen", f"Op {numero_doc} ({tipo}) — {len(items)} ítems")
                        ok(f"Operación registrada: {len(items)} ítem(s), stock actualizado"); st.rerun()
                    except Exception as e: err(e)
    with tabs[2]:
        df_ops = fetch("operacion_almacen")
        if not df_ops.empty:
            opciones = {f"{r['numero_doc']} ({r['tipo']})": r["id"] for _, r in df_ops.iterrows()}
            sel = st.selectbox("Ver detalle de operación", list(opciones.keys()), key="sel_op_detalle")
            oid = opciones[sel]
            det = supabase.table("detalle_operacion").select("*, producto(codigo,nombre)").eq("id_operacion", oid).execute()
            if det.data:
                rows = []
                for d in det.data:
                    p = d.get("producto", {})
                    rows.append({"Código": p.get("codigo",""), "Producto": p.get("nombre",""),
                                 "Cantidad": d["cantidad"], "Precio unit.": d["precio_unitario"], "Subtotal": d["subtotal"]})
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                empty_state("📋", "Sin ítems en esta operación", "")
        else:
            empty_state("🔄", "Sin operaciones", "")


# =============================================================================
# SECCIÓN 18: PÁGINA — MOVIMIENTOS (solo lectura)
# =============================================================================

def render_movimientos():
    """
    Renderiza la página del historial de movimientos de stock.
    Es una vista de SOLO LECTURA; los movimientos se generan automáticamente
    al registrar operaciones de almacén, nunca manualmente.
    Características:
        - Filtro por tipo (entrada/salida), nombre de producto y número de doc.
        - Tabla ordenada del más reciente al más antiguo.
        - Contador de registros visibles vs. total de movimientos.
        - Columnas mostradas: fecha, documento, código, producto, tipo,
          cantidad y saldo resultante.
    """
    render_header("Movimientos", "Historial cronológico de cambios de stock (solo lectura)")
    st.info("Registro de solo lectura. Los movimientos se generan automáticamente al registrar operaciones.")
    df = fetch("movimiento", "*, producto(codigo,nombre), operacion_almacen(numero_doc)")
    if df.empty:
        empty_state("📋", "Sin movimientos registrados", "Los movimientos se generan automáticamente al registrar operaciones")
    else:
        if "producto" in df.columns:
            df["prod_codigo"] = df["producto"].apply(lambda x: x.get("codigo","") if isinstance(x, dict) else "")
            df["prod_nombre"] = df["producto"].apply(lambda x: x.get("nombre","") if isinstance(x, dict) else "")
        if "operacion_almacen" in df.columns:
            df["num_doc"] = df["operacion_almacen"].apply(lambda x: x.get("numero_doc","") if isinstance(x, dict) else "")
        col1, col2, col3 = st.columns(3)
        filtro_tipo = col1.selectbox("Tipo", ["Todos","entrada","salida"])
        filtro_prod = col2.text_input("Buscar producto")
        filtro_doc  = col3.text_input("Buscar N° documento")
        vista = df.copy()
        if filtro_tipo != "Todos":
            vista = vista[vista["tipo"] == filtro_tipo]
        if filtro_prod:
            vista = vista[vista["prod_nombre"].str.contains(filtro_prod, case=False, na=False)]
        if filtro_doc:
            vista = vista[vista["num_doc"].str.contains(filtro_doc, case=False, na=False)]
        vista     = vista.sort_values("fecha", ascending=False)
        show_cols = [c for c in ["fecha","num_doc","prod_codigo","prod_nombre","tipo","cantidad","saldo"] if c in vista.columns]
        rename    = {"fecha":"Fecha","num_doc":"Documento","prod_codigo":"Código",
                     "prod_nombre":"Producto","tipo":"Tipo","cantidad":"Cantidad","saldo":"Saldo"}
        st.dataframe(vista[show_cols].rename(columns=rename), use_container_width=True, hide_index=True)
        st.caption(f"Mostrando {len(vista)} de {len(df)} movimientos")


# =============================================================================
# SECCIÓN 19: ROUTER PRINCIPAL (punto de entrada de la app)
# =============================================================================
# Descripción: Bloque de control principal que decide qué renderizar.
#   - Si el usuario NO está autenticado → muestra solo la pantalla de login.
#   - Si está autenticado:
#       1. Renderiza el sidebar y obtiene la sección seleccionada.
#       2. Renderiza el chatbot ARIA en la barra lateral.
#       3. Según la selección del menú, llama a la función de página correspondiente.
#   Este patrón de "router" es común en apps Streamlit multi-página sin
#   usar la funcionalidad nativa de pages/ de Streamlit.
# =============================================================================

if not st.session_state.authenticated:
    render_login()
else:
    section = render_sidebar()
    render_chatbot()
    if   section == "📊  Dashboard":           render_dashboard()
    elif section == "📦  Productos":           render_productos()
    elif section == "🏷️  Categorías":          render_categorias()
    elif section == "🏭  Proveedores":         render_proveedores()
    elif section == "🛒  Órdenes de Compra":   render_ordenes()
    elif section == "🔄  Operaciones Almacén": render_operaciones()
    elif section == "📋  Movimientos":         render_movimientos()
