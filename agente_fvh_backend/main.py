# -*- coding: utf-8 -*-
"""
API del Agente FVH
===================

Expone el agente (triaje + RAG + LangGraph) definido en `rag_agent.py`
como un servicio HTTP que el frontend (agente_fvh.html) consume.

Correr localmente:
    uvicorn main:app --reload --port 8000

Endpoints:
    GET  /health      -> chequeo de salud
    POST /consultar   -> {"pregunta": "..."} -> respuesta del agente
"""

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

logger = logging.getLogger("agente_fvh.api")

app = FastAPI(
    title="Agente FVH API",
    description="Agente experto en Forraje Verde Hidropónico (FVH): triaje + RAG + LangGraph.",
    version="1.0.0",
)

# --------------------------------------------------------------------------
# CORS: permite que el frontend (servido desde otro origen, ej. GitHub Pages,
# Netlify, o simplemente abierto como archivo local) pueda llamar a esta API.
# En producción, reemplazá "*" por el dominio real del frontend en la env var
# ALLOWED_ORIGINS (separados por coma).
# --------------------------------------------------------------------------
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "*")
allowed_origins = (
    ["*"] if allowed_origins_env.strip() == "*" else [o.strip() for o in allowed_origins_env.split(",")]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConsultaRequest(BaseModel):
    pregunta: str = Field(..., min_length=1, description="Pregunta del usuario sobre FVH")


class ConsultaResponse(BaseModel):
    decision: str
    accion_final: str
    respuesta: str
    fuentes: list[str]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/consultar", response_model=ConsultaResponse)
def consultar(payload: ConsultaRequest):
    pregunta = payload.pregunta.strip()
    if not pregunta:
        raise HTTPException(status_code=400, detail="La pregunta no puede estar vacía.")

    try:
        # Import diferido para que el índice FAISS se construya recién al
        # levantar el proceso (no al importar este módulo en herramientas
        # de testing, etc.)
        from rag_agent import ejecutar_agente

        resultado = ejecutar_agente(pregunta)
        return resultado
    except Exception as e:  # noqa: BLE001
        logger.exception("Error ejecutando el agente")
        raise HTTPException(status_code=500, detail=f"Error del agente: {e}") from e
