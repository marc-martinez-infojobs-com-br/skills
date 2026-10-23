# Cómo instalar y replicar la Skill `models-tokens` en OpenCode (macOS, Linux y Windows 11)

Esta guía explica qué archivos componen la skill **`models-tokens`** y cómo cualquier compañero puede instalarla en su entorno de **OpenCode** (tanto en **macOS / Linux** como en **Windows 11**) para consultar en tiempo real los modelos disponibles (todos o filtrados por `copilot`, `google`, `opencode`, `ollama`), sus costes en créditos y su clasificación en **BenchLM.ai** mediante el comando `/tokens`.

---

## 1. Comandos disponibles

Una vez instalada, puedes usarla desde cualquier sesión de OpenCode:

- `/tokens` → Muestra la tabla con **todos** los modelos de código/agentes definidos.
- `/tokens copilot` → Muestra solo los modelos de **GitHub Copilot** (`github-copilot/`).
- `/tokens google` → Muestra solo los modelos de **Google** (`google/`).
- `/tokens opencode` → Muestra solo los modelos gratuitos de **OpenCode** (`opencode/`).
- `/tokens ollama` → Muestra solo los modelos locales de **Ollama** (`ollama/`).

---

## 2. Archivos que componen la solución

Para que la skill y el comando `/tokens` funcionen globalmente en cualquier proyecto, intervienen **3 ficheros**:

### En macOS / Linux (`~/.config/opencode/`)
```text
~/.config/opencode/
├── opencode.jsonc                         # (1) Registra el comando global /tokens con $ARGUMENTS
└── skills/
    └── models-tokens/
        ├── SKILL.md                       # (2) Definición e instrucciones de la skill
        └── scripts/
            └── fetch_tokens.py            # (3) Script que consulta OpenCode + BenchLM.ai
```

### En Windows 11 (`%USERPROFILE%\.config\opencode\`)
```text
C:\Users\<tu-usuario>\.config\opencode\
├── opencode.jsonc                         # (1) Registra el comando global /tokens con $ARGUMENTS
└── skills\
    └── models-tokens\
        ├── SKILL.md                       # (2) Definición e instrucciones de la skill
        └── scripts\
            └── fetch_tokens.py            # (3) Script que consulta OpenCode + BenchLM.ai
```

| Archivo | Función |
| :--- | :--- |
| `skills/models-tokens/SKILL.md` | Define el nombre, descripción y reglas de ejecución para que OpenCode detecte la skill en macOS, Linux y Windows 11. |
| `skills/models-tokens/scripts/fetch_tokens.py` | Ejecuta `opencode api get /api/model`, filtra modelos de código/agentes (y proveedor si se pasa argumento), cruza con `leaderboard.json` y `models.json` de BenchLM.ai y genera la tabla Markdown + recomendaciones. Compatible con UTF-8 en Windows 11 y macOS/Linux. |
| `opencode.jsonc` (o `opencode.json`) | Registra el comando `/tokens` con soporte para `$ARGUMENTS` dentro de la clave `"commands"`. |

---

## 3. Requisitos previos

- Tener **OpenCode** instalado.
- Tener **Python 3** instalado:
  - **macOS / Linux:** `python3 --version`
  - **Windows 11:** `python --version` (se puede instalar desde Microsoft Store o con `winget install Python.Python.3.12`).

---

## 4. Pasos de instalación

### 🍎 Opción A: Instalación en macOS / Linux

#### Paso 1: Copiar la carpeta de la skill
Ejecuta en tu terminal (situado en la carpeta donde tengas `models_tokens`):

```bash
mkdir -p ~/.config/opencode/skills/models-tokens
cp -R ./models_tokens/* ~/.config/opencode/skills/models-tokens/
chmod +x ~/.config/opencode/skills/models-tokens/scripts/fetch_tokens.py
```

#### Paso 2: Registrar el comando `/tokens`
Abre `~/.config/opencode/opencode.jsonc` (o `~/.config/opencode/opencode.json`) y añade el bloque `"commands"` en el nivel raíz del JSON:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  // ... resto de tu configuración ...
  "commands": {
    "tokens": {
      "description": "Mostrar modelos disponibles (todos o filtrados por copilot, google, opencode, ollama), costes y Score",
      "template": "Carga y sigue la skill models-tokens para consultar dinámicamente los modelos disponibles (filtro de proveedor: '$ARGUMENTS') y presentar la tabla solicitada."
    }
  }
}
```

#### Paso 3: Verificar la instalación
```bash
opencode debug config
python3 ~/.config/opencode/skills/models-tokens/scripts/fetch_tokens.py
python3 ~/.config/opencode/skills/models-tokens/scripts/fetch_tokens.py copilot
```

---

### 🪟 Opción B: Instalación en Windows 11

#### Paso 1: Copiar la carpeta de la skill

**En PowerShell** (situado en la carpeta donde tengas `models_tokens`):

```powershell
New-Item -ItemType Directory -Force -Path "$HOME\.config\opencode\skills\models-tokens" | Out-Null
Copy-Item -Path ".\models_tokens\*" -Destination "$HOME\.config\opencode\skills\models-tokens\" -Recurse -Force
```

**O en Símbolo del sistema (CMD):**

```cmd
mkdir "%USERPROFILE%\.config\opencode\skills\models-tokens"
xcopy /E /I /Y "models_tokens\*" "%USERPROFILE%\.config\opencode\skills\models-tokens\"
```

#### Paso 2: Registrar el comando `/tokens`
Abre el archivo de configuración global de OpenCode en Windows 11:
- Ruta en PowerShell: `notepad "$HOME\.config\opencode\opencode.jsonc"` (o `opencode.json` si usas `.json`)
- Ruta en el Explorador de archivos: `%USERPROFILE%\.config\opencode\opencode.jsonc`

Añade el bloque `"commands"` en el nivel raíz del JSON (si el archivo no existía, créalo con este contenido):

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  // ... resto de tu configuración ...
  "commands": {
    "tokens": {
      "description": "Mostrar modelos disponibles (todos o filtrados por copilot, google, opencode, ollama), costes y Score",
      "template": "Carga y sigue la skill models-tokens para consultar dinámicamente los modelos disponibles (filtro de proveedor: '$ARGUMENTS') y presentar la tabla solicitada."
    }
  }
}
```

#### Paso 3: Verificar la instalación en Windows 11

**En PowerShell:**
```powershell
opencode debug config
python "$HOME\.config\opencode\skills\models-tokens\scripts\fetch_tokens.py"
python "$HOME\.config\opencode\skills\models-tokens\scripts\fetch_tokens.py" copilot
```

**En CMD:**
```cmd
opencode debug config
python "%USERPROFILE%\.config\opencode\skills\models-tokens\scripts\fetch_tokens.py"
python "%USERPROFILE%\.config\opencode\skills\models-tokens\scripts\fetch_tokens.py" copilot
```

---

## 5. Qué muestra el reporte `/tokens`

1. **Tabla ordenada de mayor a menor `Score` (BenchLM.ai):**
   - **Modelo (contexto):** Nombre del modelo con su ventana de contexto redondeada (`1M`, `500K`, `400K`, `256K`, `200K`).
   - **Provider:** Proveedor del modelo (`copilot`, `google`, `opencode`, `ollama`).
   - **Input / Output / Cache Read:** Créditos por 1M de tokens (`cost × 100`).
   - **Cost:** Clasificación automática según `max(Input, Output)`:
     - `FREE` (modelos gratuitos de `opencode` o locales de `ollama`)
     - `LOW` ≤ 500
     - `MEDIUM` < 2000
     - `HIGH` ≥ 2000
   - **Score:** Puntuación oficial de BenchLM.ai con su `#posición` (o puntuación provisional resaltada en otro color sin ranking si aún no está en el leaderboard principal).
2. **Resaltado visual en la tabla:**
   - **Negrita + icono (`🧠`, `🛠️`, `💻`):** El modelo ganador (#1) de cada una de las 3 categorías de tarea.
   - **Color de código (`...`):** Las alternativas #2 y #3 recomendadas para cada tarea.
3. **Modelos Recomendados por Tarea (por orden):**
   - 🧠 **Brainstorming, Especificación y Plan**
   - 🛠️ **Implementaciones generales, uso general**
   - 💻 **Implementaciones guiadas o sencillas**
