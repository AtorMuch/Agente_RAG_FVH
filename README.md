# Proyecto Agente FVH — Backend + Frontend

Este paquete contiene los dos componentes conectados:

```
agente_fvh_proyecto/
├── agente_fvh.html          # Frontend: la app de chat (abrir en el navegador)
└── agente_fvh_backend/      # Backend: API en Python (FastAPI + LangGraph + RAG)
    ├── main.py               # Endpoints /health y /consultar
    ├── rag_agent.py          # Triaje + RAG + grafo LangGraph
    ├── requirements.txt
    ├── Dockerfile
    ├── .env.example
    ├── README.md             # Instrucciones detalladas del backend
    └── knowledge_base/       # Los 4 PDFs del manual FAO (ya incluidos)
```

## Pasos rápidos

1. **Backend:**
   ```bash
   cd agente_fvh_backend
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env   # y poné tu OPENAI_API_KEY en .env
   uvicorn main:app --reload --port 8000
   ```
   La primera vez tarda 1-2 minutos: lee los 4 PDFs, genera los embeddings y arma el índice FAISS (queda cacheado en `faiss_index/` para los próximos arranques).

2. **Frontend:**
   Abrí `agente_fvh.html` en el navegador. Ya está configurado para apuntar a `http://localhost:8000`. Si vas a correr el backend en otra URL (por ejemplo, después de desplegarlo), editá esta línea al principio del `<script>` final del HTML:
   ```js
   const API_BASE_URL = "http://localhost:8000";
   ```

3. **Probar:** escribí una pregunta sobre FVH (o usá los chips sugeridos) y vas a ver el pipeline triaje → responder/fuera_tema/asesor funcionando contra tu backend real.

Para instrucciones de despliegue en producción (Docker, Render, Railway, etc.), ver `agente_fvh_backend/README.md`.
