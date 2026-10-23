# OpenCode Skills Repository

Repositorio centralizado de **Skills para OpenCode** diseñadas para automatizar flujos de trabajo y utilidades de desarrollo en equipo (compatible con **macOS**, **Linux** y **Windows 11**).

---

## 📚 Skills disponibles

### 1. [`models-tokens`](./models_tokens)
Consulta dinámicamente en tiempo real los modelos de código y agentes configurados en **OpenCode** (todos o filtrados por proveedor: `copilot`, `google`, `opencode`, `ollama`), extrae su ventana de contexto y sus costes en créditos, y los cruza con el ranking público de **[BenchLM.ai](https://benchlm.ai/)** (`Score`).

- **Comando:** `/tokens` (o `/tokens copilot`, `/tokens google`, `/tokens opencode`, `/tokens ollama`).
- **Incluye:**
  - Tabla ordenada de mayor a menor `Score` con los tramos de contexto disponibles (`200K / 1M`, `100K / 1M`, `272K / 1M`, etc.), costes por tramo obtenidos prioritariamente de **OpenRouter** (`Input`, `Output`, `Cache Read`, `Cache Write`) con fallback a OpenCode, y categoría de coste (`FREE`, `LOW`, `MEDIUM`, `HIGH`).
  - Resaltado en la propia tabla del modelo ganador (`🧠`, `🛠️`, `💻`) y las alternativas (#2 y #3) para cada tipo de tarea.
  - Recomendación directa de los 3 mejores modelos por orden para:
    - 🧠 **Brainstorming, Especificación y Plan**
    - 🛠️ **Implementaciones generales, uso general**
    - 💻 **Implementaciones guiadas o sencillas**
- 📖 **[Ver guía de instalación y uso detallada →](./models_tokens/README.md)**
