# -*- coding: utf-8 -*-
"""
Agente FVH — Frontend en Streamlit
====================================

Interfaz de chat que consume el backend FastAPI (agente_fvh_backend/)
desplegado en Render (o donde sea). No ejecuta el agente localmente:
solo hace POST a {API_BASE_URL}/consultar y muestra la respuesta.

Deploy: Streamlit Community Cloud, apuntando este archivo como entrypoint.
"""

import requests
import streamlit as st

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

st.set_page_config(
    page_title="Agente FVH — Forraje Verde Hidropónico",
    page_icon="🌱",
    layout="centered",
)

# URL del backend. En Streamlit Cloud, configurala en:
# Settings -> Secrets, como:
#   API_BASE_URL = "https://tu-backend.onrender.com"
API_BASE_URL = st.secrets.get("API_BASE_URL", "http://localhost:8000")

MSG_FUERA_TEMA = (
    "No lo sé. Solo soy un asistente experto en Forraje Verde Hidropónico (FVH), "
    "así que no puedo ayudarte con ese tema."
)
MSG_ASESOR = (
    "Voy a comunicarte con un asesor humano para que te ayude con esto. "
    "En breve alguien del equipo se pondrá en contacto contigo."
)

FUENTES_INFO = {
    "ah472s00.pdf": "Primera parte — Antecedentes, ventajas y desventajas",
    "ah472s01.pdf": "Segunda parte — Métodos, instalaciones, fertilización",
    "ah472s02.pdf": "Tercera parte — Alimentación animal",
    "ah472s03.pdf": "Cuarta parte — Costos e impacto económico",
}

EJEMPLOS = [
    "¿Qué es el Forraje Verde Hidropónico?",
    "¿Cuáles son las ventajas del FVH frente al forraje tradicional?",
    "¿Qué semillas se pueden utilizar para producir FVH?",
    "¿Cuánto tiempo tarda la producción?",
    "¿Cuál es el costo aproximado de producción?",
    "Quiero hablar con un asesor",
]

# --------------------------------------------------------------------------
# Backend call
# --------------------------------------------------------------------------


def consultar_agente(pregunta: str) -> dict:
    resp = requests.post(
        f"{API_BASE_URL}/consultar",
        json={"pregunta": pregunta},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------

st.title("🌱 Agente FVH")
st.caption("Forraje Verde Hidropónico · Manual Técnico FAO — triaje + RAG + LangGraph")

with st.sidebar:
    st.subheader("Flujo del agente")
    st.markdown(
        "`triaje` → **responder** (RAG sobre el manual) / **fuera_tema** / **asesor**"
    )
    st.divider()
    st.subheader("Base documental")
    for archivo, desc in FUENTES_INFO.items():
        st.markdown(f"- **{archivo}**: {desc}")
    st.divider()
    st.caption(
        "Manual Técnico FVH, FAO — Oficina Regional para América Latina y el Caribe, "
        "Santiago de Chile, 2001."
    )
    st.caption(f"Backend: `{API_BASE_URL}`")

if "history" not in st.session_state:
    st.session_state.history = []  # list of dicts: role, content, route, fuentes

# Botones de ejemplo (solo si no hay conversación todavía)
if not st.session_state.history:
    st.markdown("Preguntá sobre FVH, o probá uno de estos ejemplos:")
    cols = st.columns(2)
    for i, ej in enumerate(EJEMPLOS):
        if cols[i % 2].button(ej, key=f"ej_{i}", use_container_width=True):
            st.session_state.pending_question = ej

# Render historial
for turn in st.session_state.history:
    with st.chat_message(turn["role"]):
        if turn["role"] == "assistant" and turn.get("route"):
            st.caption(f"ruta: `{turn['route']}`")
        st.markdown(turn["content"])
        if turn.get("fuentes"):
            st.caption("Fuentes: " + ", ".join(turn["fuentes"]))

# Input de chat
pregunta = st.chat_input("Escribí tu pregunta sobre FVH…")
if "pending_question" in st.session_state:
    pregunta = st.session_state.pop("pending_question")

if pregunta:
    st.session_state.history.append({"role": "user", "content": pregunta})
    with st.chat_message("user"):
        st.markdown(pregunta)

    with st.chat_message("assistant"):
        with st.spinner("Consultando al agente…"):
            try:
                resultado = consultar_agente(pregunta)
                accion = resultado.get("accion_final") or resultado.get("decision")
                respuesta = resultado.get("respuesta", MSG_FUERA_TEMA)
                fuentes = resultado.get("fuentes", [])

                st.caption(f"ruta: `{accion}`")
                st.markdown(respuesta)
                if fuentes:
                    st.caption("Fuentes: " + ", ".join(fuentes))

                st.session_state.history.append(
                    {
                        "role": "assistant",
                        "content": respuesta,
                        "route": accion,
                        "fuentes": fuentes,
                    }
                )
            except requests.exceptions.RequestException as e:
                error_msg = f"No se pudo conectar con el backend ({API_BASE_URL}): {e}"
                st.error(error_msg)
                st.session_state.history.append({"role": "assistant", "content": error_msg})
