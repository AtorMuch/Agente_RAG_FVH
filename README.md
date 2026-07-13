# Agente RAG - Forraje Verde Hidropónico (FVH)

Agente experto en Forraje Verde Hidropónico (FVH), construido con **LangGraph** + **RAG**,
basado en el Manual Técnico de la FAO.

## Arquitectura

El flujo del agente clasifica cada pregunta del usuario mediante un nodo de **triaje** y la
enruta a una de tres rutas:

1. **RESPONDER** → Se ejecuta la cadena RAG sobre el manual FAO (embeddings + FAISS + LLM).
2. **FUERA_TEMA** → El agente responde que no puede ayudar, ya que solo es experto en FVH.
3. **ASESOR** → Se deriva al usuario a un asesor humano con un mensaje predefinido.

```
START -> triaje -> [responder | fuera_tema | asesor] -> END
```

## Tecnologías

- `langchain` / `langchain-openai` / `langchain-community` / `langchain-classic`
- `langgraph` (orquestación del flujo como grafo de estados)
- `faiss-cpu` (vector store)
- `pymupdf` (carga de PDFs)
- Modelo LLM: `gpt-4.1-mini`
- Modelo de embeddings: `text-embedding-3-small`

## Estructura del repositorio

```
agente-fvh/
├── agente_rag_de_fvh.py     # Script principal del agente
├── requirements.txt
├── knowledge_base/          # PDFs del manual FAO, segmentados por parte
│   ├── ah472s00.pdf         # Portada, índice y Primera Parte (antecedentes, ventajas/desventajas)
│   ├── ah472s01.pdf         # Segunda Parte (métodos, instalaciones, factores de producción, fertilización)
│   ├── ah472s02.pdf         # Tercera Parte (resultados en alimentación animal)
│   └── ah472s03.pdf         # Cuarta Parte (costos de producción e impacto económico) + conclusiones
├── docs/
│   └── ejemplos_uso.md      # Ejemplos de preguntas y respuestas del agente por cada ruta
├── .gitignore
└── README.md
```

## Base documental (RAG)

El agente responde exclusivamente con base en el **Manual Técnico "Forraje Verde Hidropónico"**
de la FAO (Oficina Regional para América Latina y el Caribe, 2001), segmentado en 4 archivos PDF
ubicados en `knowledge_base/`. El manual cubre:

- **Primera parte:** antecedentes, justificación, ventajas y desventajas del FVH.
- **Segunda parte:** métodos de producción, instalaciones, factores ambientales, fertilización y soluciones nutritivas.
- **Tercera parte:** resultados de la alimentación animal con FVH (vacas lecheras, terneros, corderos, conejos).
- **Cuarta parte:** costos de producción e impacto económico.

> La FAO autoriza la reproducción fiel, completa o parcial del manual siempre que no tenga fines
> comerciales y se mencione la fuente (ver portada del documento).

## Cómo ejecutarlo

### Opción A: Google Colab (como fue desarrollado originalmente)

1. Abrir el notebook en Colab.
2. Guardar la API key de OpenAI en el gestor de secretos de Colab con el nombre `OPENAI_API_KEY`.
3. Subir los PDFs del manual FAO a `/content/`.
4. Ejecutar las celdas en orden.

### Opción B: Local

1. Clonar el repositorio:
   ```bash
   git clone https://github.com/<tu-usuario>/agente-fvh.git
   cd agente-fvh
   ```
2. Crear entorno virtual e instalar dependencias:
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Crear un archivo `.env` con tu API key:
   ```
   OPENAI_API_KEY=tu_api_key_aqui
   ```
4. Colocar los PDFs del manual FAO en `knowledge_base/`.
5. Ejecutar el script.

## Ejemplo de uso

```python
respuesta = grafo.invoke({"pregunta": "¿Cuáles son las ventajas del FVH frente al forraje tradicional?"})
print(respuesta["respuesta"])
```

## Ejemplos de uso

Ver [`docs/ejemplos_uso.md`](docs/ejemplos_uso.md) para ejemplos de preguntas y respuestas
esperadas en cada una de las tres rutas del agente (`RESPONDER`, `FUERA_TEMA`, `ASESOR`),
junto con un espacio para pegar la salida real de la ejecución del script como evidencia.

## Estado del despliegue

Este proyecto fue desarrollado y probado en Google Colab. El despliegue en la nube
(Oracle Cloud Infrastructure) queda pendiente como trabajo futuro.

## Licencia

El código de este repositorio se distribuye bajo licencia MIT (ver [`LICENSE`](LICENSE)).
El manual FAO incluido en `knowledge_base/` mantiene los términos de uso definidos por la
FAO (reproducción autorizada sin fines comerciales, citando la fuente).

## Autor

<!-- Agrega tu nombre / datos del curso aquí -->
