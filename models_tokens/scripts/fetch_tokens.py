#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import urllib.request

# Ensure UTF-8 output on Windows 11 terminals (PowerShell / CMD)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

LEADERBOARD_URL = "https://benchlm.ai/data/leaderboard.json"
MODELS_URL = "https://benchlm.ai/data/models.json"

EXCLUDED_ID_KEYWORDS = (
    "image",
    "live",
    "computer-use",
    "deep-research",
    "embedding",
    "lyria",
    "tts",
    "transcribe",
)

SLUG_ALIASES = {
    "beam-free": "reflection-beam",
    "nemotron-3-5-super-vl": "nemotron-3-5-super-vl-120b-a12b",
    "nemotron-3-5-lightning": "nemotron-3-5-lightning-30b-a3b-nvfp4",
    "gemini-flash": "gemini-3-7-flash",
    "gemini-flash-lite": "gemini-3-5-flash-lite",
    "gemini-pro": "gemini-3-1-pro",
    "gemma4": "gemma-4-e4b",
    "gemma4:e4b": "gemma-4-e4b",
    "gemma4-e4b": "gemma-4-e4b",
}


def fetch_json(url: str):
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "opencode-models-tokens/1.0"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        curl_bin = "curl.exe" if os.name == "nt" else "curl"
        out = subprocess.check_output(
            [curl_bin, "-sSL", "--fail", "-H", "User-Agent: opencode-models-tokens/1.0", url],
            text=True,
            encoding="utf-8",
        )
        return json.loads(out)


def get_opencode_models():
    out = subprocess.check_output(
        ["opencode", "api", "get", "/api/model"],
        text=True,
        encoding="utf-8",
        shell=(os.name == "nt"),
    )
    data = json.loads(out)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ("models", "data"):
            if k in data and isinstance(data[k], list):
                return data[k]
    return []


def is_coding_agent_model(m: dict) -> bool:
    caps = m.get("capabilities") or {}
    if not caps.get("tools", False):
        return False
    outputs = caps.get("output") or []
    if "image" in outputs or "audio" in outputs:
        return False
    mid = str(m.get("id") or m.get("modelID") or "").lower()
    if any(k in mid for k in EXCLUDED_ID_KEYWORDS):
        return False
    return True


def normalize_provider_label(provider_id: str) -> str:
    p = provider_id.strip().lower()
    if p in ("github-copilot", "copilot"):
        return "copilot"
    return p


def normalize_filter_arg(filter_arg: str) -> str:
    f = filter_arg.strip().lower().strip("'\"`").rstrip("/")
    if f in ("", "all", "todos", "*", "$arguments"):
        return ""
    if f in ("copilot", "github-copilot"):
        return "copilot"
    return f


def to_benchlm_slug(model_id: str) -> str:
    raw = model_id.strip().lower()
    if raw in SLUG_ALIASES:
        return SLUG_ALIASES[raw]
    slug = raw.replace(":", "-").replace(".", "-").replace("gemma4-", "gemma-4-")
    for suffix in (
        "-free",
        "-fast",
        "-latest",
        "-preview-customtools",
        "-preview",
        "-it",
    ):
        if slug.endswith(suffix):
            slug = slug[: -len(suffix)]
    return SLUG_ALIASES.get(slug, slug)


def format_context(tokens) -> str:
    if not tokens:
        return "N/D"
    if tokens >= 1_000_000:
        return f"{round(tokens / 1_000_000):.0f}M"
    return f"{round(tokens / 1000):.0f}K"


def format_credit(val) -> str:
    if val is None:
        return "0"
    credits = val * 100
    return f"{credits:.6f}".rstrip("0").rstrip(".")


def cost_tier(provider_label: str, inp, out) -> str:
    if provider_label in ("opencode", "ollama"):
        return "FREE"
    if inp is None and out is None:
        return "FREE"
    m = max((inp or 0) * 100, (out or 0) * 100)
    if m == 0:
        return "FREE"
    if m <= 500:
        return "LOW"
    if m < 2000:
        return "MEDIUM"
    return "HIGH"


def main():
    raw_filter = " ".join(sys.argv[1:]).strip()
    requested_provider = normalize_filter_arg(raw_filter)

    opencode_models = get_opencode_models()
    lb = fetch_json(LEADERBOARD_URL)
    mods = fetch_json(MODELS_URL)

    overall_map = {item["slug"]: item for item in lb.get("items", [])}
    model_list = mods.get("items") or mods.get("models") or []
    model_map = {item["slug"]: item for item in model_list}

    coding_models = [m for m in opencode_models if is_coding_agent_model(m)]
    available_providers = {
        normalize_provider_label(
            str(
                m.get("providerID")
                or m.get("provider")
                or (m.get("settings") or {}).get("provider")
                or ""
            )
        )
        for m in coding_models
    }

    # If the requested provider does not exist, fallback to showing all providers
    if requested_provider and requested_provider not in available_providers:
        active_provider_filter = ""
    else:
        active_provider_filter = requested_provider

    show_provider_col = active_provider_filter == ""

    grouped = {}
    for m in coding_models:
        raw_provider = str(
            m.get("providerID")
            or m.get("provider")
            or (m.get("settings") or {}).get("provider")
            or ""
        )
        provider_label = normalize_provider_label(raw_provider)
        if active_provider_filter and provider_label != active_provider_filter:
            continue

        model_id = m.get("id") or m.get("modelID") or m.get("name") or ""
        raw_name = (m.get("name") or model_id).replace(" (latest)", "")
        ctx = format_context((m.get("limit") or {}).get("context"))
        cost = (m.get("cost") or [{}])[0] if m.get("cost") else {}
        cache = cost.get("cache") or {}

        inp = cost.get("input", 0)
        out = cost.get("output", 0)
        c_read = cache.get("read", 0)
        tier = cost_tier(provider_label, inp, out)
        max_credit = 0 if tier == "FREE" else max((inp or 0) * 100, (out or 0) * 100)

        slug = to_benchlm_slug(model_id)
        ov = overall_map.get(slug)
        md = model_map.get(slug) or {}
        md_scores = md.get("scores") or {}

        if ov and ov.get("score") is not None and ov.get("rank") is not None:
            raw_score = ov["score"]
            ov_val = float(raw_score)
            score_str = f"{raw_score} (#{ov['rank']})"
        else:
            fallback_ov = (
                md_scores.get("displayScore")
                or md_scores.get("verifiedDisplayScore")
                or md.get("provisionalDisplayScore")
            )
            if fallback_ov and float(fallback_ov) > 0:
                ov_val = float(fallback_ov)
                score_str = f"`{fallback_ov}`"
            else:
                ov_val = -1.0
                score_str = "N/D"

        label = f"{raw_name} ({ctx})"
        group_key = model_id.strip().lower()

        if group_key not in grouped:
            grouped[group_key] = {
                "key": group_key,
                "id": model_id,
                "providers": [provider_label],
                "name": raw_name,
                "label": label,
                "inp": "0" if tier == "FREE" else format_credit(inp),
                "out": "0" if tier == "FREE" else format_credit(out),
                "c_read": "0" if tier == "FREE" else format_credit(c_read),
                "tier": tier,
                "max_credit": max_credit,
                "ov_val": ov_val,
                "score_str": score_str,
            }
        else:
            if provider_label not in grouped[group_key]["providers"]:
                grouped[group_key]["providers"].append(provider_label)

    rows = list(grouped.values())
    for r in rows:
        r["provider_str"] = ", ".join(r["providers"])

    rows.sort(key=lambda r: (-r["ov_val"], r["max_credit"], r["label"]))

    ranked = [r for r in rows if r["ov_val"] > 0]
    pool = ranked if ranked else rows

    top_frontier = pool[:3]
    medium_pool = [r for r in pool if r["tier"] == "MEDIUM"]
    top_general = (medium_pool if medium_pool else pool)[:3]
    low_free_pool = [r for r in pool if r["tier"] in ("LOW", "FREE")]
    top_simple = (low_free_pool if low_free_pool else pool)[:3]

    winner_icons = {}
    if top_frontier:
        winner_icons[top_frontier[0]["key"]] = "🧠"
    if top_general and top_general[0]["key"] not in winner_icons:
        winner_icons[top_general[0]["key"]] = "🛠️"
    if top_simple and top_simple[0]["key"] not in winner_icons:
        winner_icons[top_simple[0]["key"]] = "💻"

    runner_up_keys = {
        p["key"]
        for group in (top_frontier, top_general, top_simple)
        for p in group[1:]
        if p["key"] not in winner_icons
    }

    title_scope = (
        f"Proveedor: {active_provider_filter}"
        if active_provider_filter
        else "Todos los proveedores"
    )
    print(f"### 📊 Modelos, Costes por Token y Score ({title_scope})")
    print("*(Datos actualizados dinámicamente)*\n")

    if show_provider_col:
        print("| Modelo (contexto) | Provider | Input | Output | Cache Read | Cost | Score |")
        print("| :--- | :--- | ---: | ---: | ---: | :--- | ---: |")
    else:
        print("| Modelo (contexto) | Input | Output | Cache Read | Cost | Score |")
        print("| :--- | ---: | ---: | ---: | :--- | ---: |")

    for r in rows:
        icon = winner_icons.get(r["key"])
        clean_score = r["score_str"].strip("`")
        if show_provider_col:
            if icon:
                print(
                    f"| **{icon} {r['label']}** | **{r['provider_str']}** | **{r['inp']}** | **{r['out']}** | **{r['c_read']}** | **{r['tier']}** | **{clean_score}** |"
                )
            elif r["key"] in runner_up_keys:
                print(
                    f"| `{r['label']}` | `{r['provider_str']}` | `{r['inp']}` | `{r['out']}` | `{r['c_read']}` | `{r['tier']}` | `{clean_score}` |"
                )
            else:
                print(
                    f"| {r['label']} | {r['provider_str']} | {r['inp']} | {r['out']} | {r['c_read']} | {r['tier']} | {r['score_str']} |"
                )
        else:
            if icon:
                print(
                    f"| **{icon} {r['label']}** | **{r['inp']}** | **{r['out']}** | **{r['c_read']}** | **{r['tier']}** | **{clean_score}** |"
                )
            elif r["key"] in runner_up_keys:
                print(
                    f"| `{r['label']}` | `{r['inp']}` | `{r['out']}` | `{r['c_read']}` | `{r['tier']}` | `{clean_score}` |"
                )
            else:
                print(
                    f"| {r['label']} | {r['inp']} | {r['out']} | {r['c_read']} | {r['tier']} | {r['score_str']} |"
                )

    def fmt_picks(picks):
        if not picks:
            return "N/D"
        return " → ".join(f"`{p['name']}`" for p in picks)

    print("\n### 💡 Modelos Recomendados por Tarea (por orden)")
    print(f"- 🧠 **Brainstorming, Especificación y Plan:** {fmt_picks(top_frontier)}")
    print(f"- 🛠️ **Implementaciones generales, uso general:** {fmt_picks(top_general)}")
    print(f"- 💻 **Implementaciones guiadas o sencillas:** {fmt_picks(top_simple)}")


if __name__ == "__main__":
    main()
