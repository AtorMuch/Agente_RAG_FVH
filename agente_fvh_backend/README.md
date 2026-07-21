# Agente FVH — API

Backend que expone el agente (**triaje + RAG + LangGraph**) del repo
[`Agente_RAG_FVH`](https://github.com/AtorMuch/Agente_RAG_FVH) como una
API HTTP, para que `agente_fvh.html` (u otro frontend) pueda consultarlo.

Reemplaza el flujo original pensado para Google Colab (una celda que
corría una sola vez) por un servicio persistente: el índice FAISS se
construye una vez al arrancar (y se cachea en disco), y luego cada
pregunta llega por HTTP.

## Estructura

```
agente_fvh_backend/
├── main.py                # API FastAPI (endpoints /health y /consultar)
├── rag_agent.py            # Triaje + RAG + grafo LangGraph (lógica del agente)
├── requirements.txt
├── Dockerfile
├── .env.example
└── knowledge_base/         # <- ACÁ van los 4 PDFs del manual FAO
    ├── ah472s00.pdf
    ├── ah472s01.pdf
    ├── ah472s02.pdf
    └── ah472s03.pdf
```

Copiá los 4 PDFs que ya están en tu repo (`ah472s00.pdf` … `ah472s03.pdf`)
a la carpeta `knowledge_base/`.

## 1. Correrlo en local

```bash
cd agente_fvh_backend
python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# editá .env y poné tu OPENAI_API_KEY

uvicorn main:app --reload --port 8000
```

La primera vez que arranca, construye el índice FAISS (lee los 4 PDFs,
los trocea y genera los embeddings) y lo guarda en `faiss_index/` para
no tener que rehacerlo en cada reinicio. Este primer arranque puede
tardar uno o dos minutos.

Probalo con:

```bash
curl -X POST http://localhost:8000/consultar \
  -H "Content-Type: application/json" \
  -d '{"pregunta": "¿Cuáles son las ventajas del FVH frente al forraje tradicional?"}'
```

Respuesta esperada:

```json
{
  "decision": "RESPONDER",
  "accion_final": "RESPONDER",
  "respuesta": "...",
  "fuentes": ["ah472s00.pdf"]
}
```

## 2. Conectar el frontend (`agente_fvh.html`)

Abrí `agente_fvh.html` y en el `<script>` final editá la constante:

```js
const API_BASE_URL = "http://localhost:8000"; // o la URL donde despliegues el backend
```

Si vas a abrir el HTML directamente como archivo local (`file://`) o
desde un dominio distinto al del backend, dejá `ALLOWED_ORIGINS=*` en el
`.env` del backend (ya viene así por defecto). En producción, lo ideal
es restringirlo al dominio real donde publiques el HTML.

## 3. Desplegarlo

Cualquier servicio que corra un contenedor Docker o un proceso Python
sirve (Render, Railway, Fly.io, un droplet con Docker, Oracle Cloud,
etc.). Con el `Dockerfile` incluido:

```bash
docker build -t agente-fvh-api .
docker run -p 8000:8000 --env-file .env agente-fvh-api
```

Pasos generales en cualquier PaaS (Render/Railway como ejemplo):

1. Subí este repo (o el contenido de esta carpeta) a GitHub.
2. Creá un nuevo servicio web apuntando al repo, tipo Docker (o Python,
   usando `uvicorn main:app --host 0.0.0.0 --port $PORT` como start
   command).
3. Configurá la variable de entorno `OPENAI_API_KEY`.
4. Deploy. Vas a obtener una URL pública (ej: `https://agente-fvh.onrender.com`).
5. Poné esa URL en `API_BASE_URL` dentro de `agente_fvh.html`.

> Nota: el índice FAISS se recalcula si la carpeta `faiss_index/` no
> persiste entre despliegues (algunos PaaS gratuitos no persisten disco).
> Si eso pasa, el primer request después de cada deploy va a tardar más
> mientras se reconstruye el índice; las siguientes preguntas usan la
> caché en memoria del proceso.

## Endpoints

| Método | Ruta         | Body                          | Descripción                               |
|--------|--------------|--------------------------------|--------------------------------------------|
| GET    | `/health`    | —                              | Chequeo de salud                          |
| POST   | `/consultar` | `{ "pregunta": "string" }`     | Ejecuta triaje + (RAG / fuera_tema / asesor) |

## Variables de entorno

Ver `.env.example`. La única obligatoria es `OPENAI_API_KEY`.
