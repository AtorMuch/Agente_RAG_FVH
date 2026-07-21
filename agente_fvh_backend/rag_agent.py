# -*- coding: utf-8 -*-
"""
Agente RAG - Forraje Verde Hidropónico (FVH)
=============================================

Refactorización del notebook original (agente_rag_de_fvh.py) para correr
como un servicio persistente (en vez de un script de Colab que se ejecuta
una sola vez).

Flujo (idéntico al original):
    START -> triaje -> [responder | fuera_tema | asesor] -> END

- triaje:      clasifica la pregunta con el LLM (RESPONDER / FUERA_TEMA / ASESOR)
- responder:   ejecuta la cadena RAG (FAISS + embeddings + LLM) sobre el manual FAO
- fuera_tema:  responde que el agente solo sabe de FVH
- asesor:      deriva a un humano con un mensaje fijo

Diferencias con el notebook original:
- El índice FAISS se construye una sola vez al arrancar el proceso (y se
  cachea en disco) en vez de reconstruirse cada vez que se corre la celda.
- Los PDFs se leen desde la carpeta `knowledge_base/` en vez de `/content/`.
- Se expone una única función `ejecutar_agente(pregunta)` para ser
  consumida por la API (ver main.py).
"""

from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Dict, List, Literal, TypedDict

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agente_fvh")

# --------------------------------------------------------------------------
# Configuración
# --------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
KB_DIR = Path(os.getenv("KB_DIR", BASE_DIR / "knowledge_base"))
INDEX_DIR = Path(os.getenv("INDEX_DIR", BASE_DIR / "faiss_index"))

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-mini")
EMBEDDINGS_MODEL = os.getenv("EMBEDDINGS_MODEL", "text-embedding-3-small")

if not os.getenv("OPENAI_API_KEY"):
    logger.warning(
        "OPENAI_API_KEY no está definida. Configurala en el entorno o en un "
        "archivo .env antes de levantar el servicio."
    )

# --------------------------------------------------------------------------
# LLM
# --------------------------------------------------------------------------

from langchain_openai import ChatOpenAI, OpenAIEmbeddings  # noqa: E402

llm = ChatOpenAI(model=LLM_MODEL, temperature=0)

# --------------------------------------------------------------------------
# Nodo de triaje
# --------------------------------------------------------------------------

PROMPT_TRIAJE = """
Eres el clasificador de un asistente que es experto ÚNICAMENTE en Forraje Verde
Hidropónico (FVH), basado en el Manual Técnico de la FAO.

Dado el mensaje del usuario, clasificalo en una de tres categorías.

Reglas:
- "RESPONDER": la pregunta trata sobre producción, ventajas, semillas, instalaciones,
  condiciones ambientales, fertilización, alimentación animal, costos, factores de
  rendimiento, o cualquier otro aspecto del Forraje Verde Hidropónico.
- "FUERA_TEMA": la pregunta NO tiene relación con FVH (otro tema, cultura general,
  charla casual, etc.).
- "ASESOR": el usuario pide explícitamente hablar con una persona, un experto humano,
  un asesor, soporte humano, o dice que quiere hablar "con alguien" en vez del bot.

Ante la duda entre RESPONDER y FUERA_TEMA, prioriza FUERA_TEMA.
"""


class TriajeOut(BaseModel):
    decision: Literal["RESPONDER", "FUERA_TEMA", "ASESOR"]


from langchain_core.messages import HumanMessage, SystemMessage  # noqa: E402

chain_de_triaje = llm.with_structured_output(TriajeOut)


def triaje(mensaje: str) -> Dict:
    salida: TriajeOut = chain_de_triaje.invoke(
        [SystemMessage(content=PROMPT_TRIAJE), HumanMessage(content=mensaje)]
    )
    return salida.model_dump()


# --------------------------------------------------------------------------
# Base documental (RAG) - construcción / carga del índice FAISS
# --------------------------------------------------------------------------

from langchain_community.document_loaders import PyMuPDFLoader  # noqa: E402
from langchain_community.vectorstores import FAISS  # noqa: E402
from langchain_text_splitters import RecursiveCharacterTextSplitter  # noqa: E402

modelo_embeddings = OpenAIEmbeddings(model=EMBEDDINGS_MODEL)


def _cargar_documentos() -> List:
    docs = []
    if not KB_DIR.exists():
        raise FileNotFoundError(
            f"No se encontró la carpeta de la base documental: {KB_DIR}. "
            "Colocá ahí los PDFs del manual FAO (ah472s00.pdf ... ah472s03.pdf)."
        )
    for pdf_path in sorted(KB_DIR.glob("*.pdf")):
        try:
            loader = PyMuPDFLoader(str(pdf_path))
            cargados = loader.load()
            for d in cargados:
                d.metadata["source_file"] = pdf_path.name
            docs.extend(cargados)
            logger.info("Archivo cargado: %s", pdf_path.name)
        except Exception as e:  # noqa: BLE001
            logger.error("Error cargando archivo %s: %s", pdf_path.name, e)
    if not docs:
        raise FileNotFoundError(
            f"No se encontraron PDFs en {KB_DIR}. Colocá ahí los 4 PDFs del manual FAO."
        )
    logger.info("Total de documentos cargados: %d", len(docs))
    return docs


def _construir_vectorstore() -> FAISS:
    """Construye el índice FAISS desde cero a partir de los PDFs."""
    docs = _cargar_documentos()
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
    chunks = splitter.split_documents(docs)
    logger.info("Total de fragmentos: %d", len(chunks))
    vectorstore = FAISS.from_documents(chunks, modelo_embeddings)
    return vectorstore


def _cargar_o_construir_vectorstore() -> FAISS:
    """Carga el índice cacheado en disco si existe; si no, lo construye y lo guarda."""
    if INDEX_DIR.exists() and any(INDEX_DIR.iterdir()):
        try:
            logger.info("Cargando índice FAISS cacheado desde %s", INDEX_DIR)
            return FAISS.load_local(
                str(INDEX_DIR),
                modelo_embeddings,
                allow_dangerous_deserialization=True,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("No se pudo cargar el índice cacheado (%s). Reconstruyendo...", e)

    vectorstore = _construir_vectorstore()
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(INDEX_DIR))
    logger.info("Índice FAISS guardado en %s", INDEX_DIR)
    return vectorstore


vectorstore = _cargar_o_construir_vectorstore()
retriever = vectorstore.as_retriever(
    search_type="similarity_score_threshold",
    search_kwargs={"score_threshold": 0.3, "k": 4},
)

# --------------------------------------------------------------------------
# Cadena RAG
# --------------------------------------------------------------------------

from langchain_classic.chains.combine_documents import create_stuff_documents_chain  # noqa: E402
from langchain_core.prompts import ChatPromptTemplate  # noqa: E402

prompt_rag = ChatPromptTemplate(
    [
        (
            "system",
            """
Eres un asistente técnico experto en Forraje Verde Hidropónico (FVH),
basado en el Manual Técnico de la FAO.

Responde siempre utilizando el contexto que te paso.
Si no hay información sobre la pregunta en el contexto, responde solo 'No lo sé'.
""",
        ),
        ("human", "Contexto: {context} \n Pregunta del usuario: {input}"),
    ]
)

document_chain = create_stuff_documents_chain(llm, prompt_rag)


def busqueda_de_respuestas_RAG(pregunta: str) -> Dict:
    documentos_relacionados = retriever.invoke(pregunta)
    if not documentos_relacionados:
        return {"respuesta": "No lo sé", "fuentes": [], "documentos_encontrados": False}

    answer = document_chain.invoke({"input": pregunta, "context": documentos_relacionados})

    if answer.rstrip(".!?") == "No lo sé":
        return {"respuesta": "No lo sé", "fuentes": [], "documentos_encontrados": False}

    fuentes = sorted({d.metadata.get("source_file", "?") for d in documentos_relacionados})
    return {"respuesta": answer, "fuentes": fuentes, "documentos_encontrados": True}


# --------------------------------------------------------------------------
# Agente con LangGraph (triaje + RAG unidos en un grafo de 3 rutas)
# --------------------------------------------------------------------------

from langgraph.graph import END, START, StateGraph  # noqa: E402


class AgentState(TypedDict, total=False):
    pregunta: str
    triaje: dict
    respuesta: str
    fuentes: List[str]
    accion_final: str


MENSAJE_FUERA_TEMA = (
    "No lo sé. Solo soy un asistente experto en Forraje Verde Hidropónico (FVH), "
    "así que no puedo ayudarte con ese tema."
)
MENSAJE_ASESOR = (
    "Voy a comunicarte con un asesor humano para que te ayude con esto. "
    "En breve alguien del equipo se pondrá en contacto contigo."
)


def nodo_triaje(state: AgentState) -> AgentState:
    return {"triaje": triaje(state["pregunta"])}


def nodo_responder(state: AgentState) -> AgentState:
    respuesta_RAG = busqueda_de_respuestas_RAG(state["pregunta"])
    if not respuesta_RAG["documentos_encontrados"]:
        return {"respuesta": MENSAJE_FUERA_TEMA, "fuentes": [], "accion_final": "FUERA_TEMA"}
    return {
        "respuesta": respuesta_RAG["respuesta"],
        "fuentes": respuesta_RAG["fuentes"],
        "accion_final": "RESPONDER",
    }


def nodo_fuera_tema(state: AgentState) -> AgentState:
    return {"respuesta": MENSAJE_FUERA_TEMA, "fuentes": [], "accion_final": "FUERA_TEMA"}


def nodo_asesor(state: AgentState) -> AgentState:
    return {"respuesta": MENSAJE_ASESOR, "fuentes": [], "accion_final": "ASESOR"}


def arista_decision_triaje(state: AgentState) -> str:
    decision = state["triaje"]["decision"]
    if decision == "RESPONDER":
        return "responder"
    elif decision == "ASESOR":
        return "asesor"
    else:
        return "fuera_tema"


workflow = StateGraph(AgentState)
workflow.add_node("triaje", nodo_triaje)
workflow.add_node("responder", nodo_responder)
workflow.add_node("fuera_tema", nodo_fuera_tema)
workflow.add_node("asesor", nodo_asesor)

workflow.add_edge(START, "triaje")
workflow.add_conditional_edges(
    "triaje",
    arista_decision_triaje,
    {"responder": "responder", "fuera_tema": "fuera_tema", "asesor": "asesor"},
)
workflow.add_edge("responder", END)
workflow.add_edge("fuera_tema", END)
workflow.add_edge("asesor", END)

grafo = workflow.compile()


# --------------------------------------------------------------------------
# Función pública consumida por la API
# --------------------------------------------------------------------------


def ejecutar_agente(pregunta: str) -> Dict:
    """Ejecuta el grafo completo (triaje -> ruta correspondiente) para una pregunta.

    Devuelve un dict con las mismas claves que usa el frontend:
        {
            "decision": "RESPONDER" | "FUERA_TEMA" | "ASESOR",
            "accion_final": "RESPONDER" | "FUERA_TEMA" | "ASESOR",
            "respuesta": str,
            "fuentes": List[str],
        }
    """
    resultado = grafo.invoke({"pregunta": pregunta})
    return {
        "decision": resultado.get("triaje", {}).get("decision", resultado.get("accion_final")),
        "accion_final": resultado.get("accion_final"),
        "respuesta": resultado.get("respuesta", MENSAJE_FUERA_TEMA),
        "fuentes": resultado.get("fuentes", []),
    }
