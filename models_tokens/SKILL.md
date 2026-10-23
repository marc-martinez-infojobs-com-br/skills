---
name: models-tokens
description: Consulta dinámicamente mediante la API local de OpenCode los modelos activos (todos o filtrados por copilot, google, opencode u ollama) y cruza sus datos con BenchLM.ai, mostrando su ventana de contexto, proveedor, costes de tokens, nivel de coste (FREE, LOW, MEDIUM, HIGH) y Score junto con recomendaciones por tipo de tarea. Usa esta skill siempre que el usuario solicite la lista de modelos, sus tokens, contexto, límites o rendimiento/clasificación, o ejecute /tokens.
---

# Models Specs, Tokens & BenchLM Score Fetcher

## Objetivo

Obtener en tiempo real la lista viva de modelos de código/agentes habilitados en OpenCode (todos o filtrados por proveedor: `copilot`, `google`, `opencode`, `ollama`), junto con sus costes de tokens, su clasificación `Score` en BenchLM.ai y recomendaciones prácticas según la relación coste/score.

## Instrucciones de Ejecución

Cuando el usuario escriba `/tokens` (con o sin filtro de proveedor, p. ej. `/tokens`, `/tokens google`, `/tokens copilot`, `/tokens opencode`, `/tokens ollama`), invoque esta skill, o pregunte por los tokens, costes o clasificación/rendimiento de sus modelos:

1. **Ejecuta el script incluido en la skill pasando el filtro de proveedor si el usuario indicó uno:**

   - En **macOS / Linux**:
     ```sh
     python3 ~/.config/opencode/skills/models-tokens/scripts/fetch_tokens.py [proveedor]
     ```
   - En **Windows 11 (PowerShell / CMD)**:
     ```powershell
     python "$HOME\.config\opencode\skills\models-tokens\scripts\fetch_tokens.py" [proveedor]
     ```
   *(Si el usuario no especificó proveedor o pidió todos, ejecútalo sin argumentos. Si el directorio base de la skill es distinto, usa la ruta `scripts/fetch_tokens.py` relativa al directorio base de la skill).*

   Este script realiza automáticamente:
   - Consulta a `opencode api get /api/model`, filtrado exclusivo de modelos de código/agentes (`capabilities.tools: true`, excluyendo modelos de imagen, audio, embeddings, live, computer-use o deep-research) y filtrado opcional por proveedor (`copilot`, `google`, `opencode`, `ollama`).
   - Redondeo de la ventana de contexto al final del nombre (`1M`, `500K`, `400K`, `256K`, `200K`).
   - Inclusión de la columna `Provider` únicamente cuando se muestran **todos** los proveedores, agrupando en una sola fila los modelos repetidos entre proveedores (p. ej. `copilot, google`). Si se filtra por un proveedor válido específico, se omite la columna `Provider`. Si el usuario pide un proveedor que no existe, se devuelve automáticamente la lista completa de todos los proveedores.
   - Conversión de `Input`, `Output` y `Cache Read` a créditos por 1M de tokens (`cost[0] × 100`).
   - Cálculo de la columna `Cost` según `max(Input, Output)` (`FREE` para `opencode`/`ollama` o coste 0, `LOW` ≤ 500, `MEDIUM` < 2000, `HIGH` ≥ 2000).
   - Cruce con `https://benchlm.ai/data/leaderboard.json` para obtener la columna `Score` con el valor original sin convertir y su posición (`(#rank)`).
   - Fallback a `https://benchlm.ai/data/models.json` cuando un modelo no aparece en el ranking principal, mostrando su puntuación provisional en código inline (otro color, ej. `` `65` ``) y sin número de ranking.
   - Ordenación de la tabla de mayor a menor `Score`.
   - Resaltado en **negrita** de toda la fila en la tabla principal para los 3 modelos ganadores (#1) de cada categoría, precedidos por su icono (`🧠`, `🛠️`, `💻`), y resaltado en código inline (`` `...` ``, sin icono) de toda la fila para las demás opciones recomendadas (#2 y #3 de cada tarea).
   - Propuesta de los **3 mejores modelos por orden** (sin repetir score ni cost, y usando código inline `` `Modelo` `` para distinguir su color del título en negrita de la tarea) para cada una de estas tareas:
     - 🧠 **Brainstorming, Especificación y Plan**
     - 🛠️ **Implementaciones generales, uso general**
     - 💻 **Implementaciones guiadas o sencillas**

2. **Imprime directamente la salida Markdown generada por el script**, sin inventar filas ni alterar las cifras.

3. **Fuentes de datos (solo bajo petición):** No incluyas las fuentes de los datos en la respuesta por defecto. Únicamente si el usuario pregunta de dónde salen los datos o las fuentes, indícale que los modelos, contextos y costes provienen de `opencode api get /api/model` (créditos por 1M = `cost × 100`) y que el `Score` proviene de [BenchLM.ai](https://benchlm.ai/data) (`leaderboard.json` para modelos con `#posición` y `models.json` para puntuaciones provisionales en otro color sin número de ranking).
