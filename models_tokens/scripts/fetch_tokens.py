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
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

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

OPENROUTER_SLUG_ALIASES = {
    "claude-opus-4.8-fast": "claude-opus-4.8",
    "gemini-flash-latest": "gemini-3.7-flash",
    "gemini-flash-lite-latest": "gemini-3.5-flash-lite",
    "gemini-pro-latest": "gemini-3.1-pro-preview",
    "gemini-3.1-pro-preview-customtools": "gemini-3.1-pro-preview",
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


def to_openrouter_key(model_id: str) -> str:
    raw = model_id.strip().lower()
    return OPENROUTER_SLUG_ALIASES.get(raw, raw)


def format_context(tokens) -> str:
    if not tokens:
        return "N/D"
    if tokens >= 1_000_000:
        return f"{round(tokens / 1_000_000):.0f}M"
    return f"{round(tokens / 1000):.0f}K"


def format_num(val: float) -> str:
    if val is None:
        return "0"
    return f"{val:.4f}".rstrip("0").rstrip(".")


def format_tier_values(values: list) -> str:
    formatted = [format_num(v) for v in values]
    # Deduplicate if all context tiers have the exact same value
    unique = []
    for f in formatted:
        if f not in unique:
            unique.append(f)
    if len(unique) == 1:
        return unique[0]
    return " / ".join(formatted)


def or_price_to_credits(val) -> float:
    if val is None or val == "":
        return 0.0
    return round(float(val) * 100_000_000.0, 4)


def oc_price_to_credits(val) -> float:
    if val is None:
        return 0.0
    return round(float(val) * 100.0, 4)


def cost_tier(is_free_provider: bool, max_credit: float) -> str:
    if is_free_provider or max_credit == 0:
        return "FREE"
    if max_credit <= 500:
        return "LOW"
    if max_credit < 2000:
        return "MEDIUM"
    return "HIGH"


def resolve_pricing_and_contexts(m: dict, provider_label: str, or_map: dict):
    model_id = str(m.get("id") or m.get("modelID") or "").strip()
    limit = m.get("limit") or {}
    max_ctx_tokens = limit.get("context")
    max_ctx_str = format_context(max_ctx_tokens)

    is_free_provider = provider_label in ("opencode", "ollama")
    if is_free_provider:
        return {
            "ctx_str": max_ctx_str,
            "inp_str": "0",
            "out_str": "0",
            "cr_str": "0",
            "cw_str": "0",
            "max_credit": 0.0,
            "tier": "FREE",
        }

    or_key = to_openrouter_key(model_id)
    or_model = or_map.get(or_key)

    # Check if OpenRouter has pricing for this model
    if or_model and or_model.get("pricing"):
        p = or_model["pricing"]
        base_inp = or_price_to_credits(p.get("prompt"))
        base_out = or_price_to_credits(p.get("completion"))
        base_cr = or_price_to_credits(p.get("input_cache_read"))
        base_cw = or_price_to_credits(p.get("input_cache_write"))

        inp_vals = [base_inp]
        out_vals = [base_out]
        cr_vals = [base_cr]
        cw_vals = [base_cw]

        overrides = p.get("overrides") or []
        ctx_tiers = []
        for ov in sorted(overrides, key=lambda x: x.get("min_prompt_tokens", 0)):
            min_tok = ov.get("min_prompt_tokens")
            if min_tok:
                ctx_tiers.append(format_context(min_tok))
            inp_vals.append(
                or_price_to_credits(ov.get("prompt"))
                if ov.get("prompt") is not None
                else base_inp
            )
            out_vals.append(
                or_price_to_credits(ov.get("completion"))
                if ov.get("completion") is not None
                else base_out
            )
            cr_vals.append(
                or_price_to_credits(ov.get("input_cache_read"))
                if ov.get("input_cache_read") is not None
                else base_cr
            )
            cw_vals.append(
                or_price_to_credits(ov.get("input_cache_write"))
                if ov.get("input_cache_write") is not None
                else base_cw
            )

        if ctx_tiers:
            ctx_tiers.append(max_ctx_str)
            ctx_str = " / ".join(dict.fromkeys(ctx_tiers))
        elif (
            model_id.lower().startswith("claude-")
            and max_ctx_tokens
            and max_ctx_tokens >= 1_000_000
        ):
            # Copilot Claude 1M models expose 200K / 1M context options
            ctx_str = f"200K / {max_ctx_str}"
        else:
            ctx_str = max_ctx_str

        max_credit = max(inp_vals + out_vals)
        tier = cost_tier(False, max_credit)
        return {
            "ctx_str": ctx_str,
            "inp_str": format_tier_values(inp_vals),
            "out_str": format_tier_values(out_vals),
            "cr_str": format_tier_values(cr_vals),
            "cw_str": format_tier_values(cw_vals),
            "max_credit": max_credit,
            "tier": tier,
        }

    # Fallback to OpenCode pricing (may include multiple cost tiers)
    costs = m.get("cost") or []
    if not costs:
        return {
            "ctx_str": max_ctx_str,
            "inp_str": "0",
            "out_str": "0",
            "cr_str": "0",
            "cw_str": "0",
            "max_credit": 0.0,
            "tier": "FREE",
        }

    inp_vals = []
    out_vals = []
    cr_vals = []
    cw_vals = []
    ctx_tiers = []
    for c in costs:
        tier_info = c.get("tier") or {}
        if tier_info.get("type") == "context" and tier_info.get("size"):
            ctx_tiers.append(format_context(tier_info["size"]))
        cache = c.get("cache") or {}
        inp_vals.append(oc_price_to_credits(c.get("input", 0)))
        out_vals.append(oc_price_to_credits(c.get("output", 0)))
        cr_vals.append(oc_price_to_credits(cache.get("read", 0)))
        cw_vals.append(oc_price_to_credits(cache.get("write", 0)))

    if ctx_tiers:
        ctx_tiers.append(max_ctx_str)
        ctx_str = " / ".join(dict.fromkeys(ctx_tiers))
    else:
        ctx_str = max_ctx_str

    max_credit = max(inp_vals + out_vals)
    tier = cost_tier(False, max_credit)
    return {
        "ctx_str": ctx_str,
        "inp_str": format_tier_values(inp_vals),
        "out_str": format_tier_values(out_vals),
        "cr_str": format_tier_values(cr_vals),
        "cw_str": format_tier_values(cw_vals),
        "max_credit": max_credit,
        "tier": tier,
    }


def main():
    raw_filter = " ".join(sys.argv[1:]).strip()
    requested_provider = normalize_filter_arg(raw_filter)

    opencode_models = get_opencode_models()
    lb = fetch_json(LEADERBOARD_URL)
    mods = fetch_json(MODELS_URL)
    or_data = fetch_json(OPENROUTER_MODELS_URL)

    overall_map = {item["slug"]: item for item in lb.get("items", [])}
    model_list = mods.get("items") or mods.get("models") or []
    model_map = {item["slug"]: item for item in model_list}

    or_map = {}
    for om in or_data.get("data") or []:
        oid = str(om.get("id") or "")
        if "/" in oid:
            short_id = oid.split("/", 1)[1].lower()
            if ":" not in short_id and short_id not in or_map:
                or_map[short_id] = om

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
        p_info = resolve_pricing_and_contexts(m, provider_label, or_map)

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

        label = f"{raw_name} ({p_info['ctx_str']})"
        group_key = model_id.strip().lower()

        if group_key not in grouped:
            grouped[group_key] = {
                "key": group_key,
                "id": model_id,
                "providers": [provider_label],
                "name": raw_name,
                "label": label,
                "inp": p_info["inp_str"],
                "out": p_info["out_str"],
                "c_read": p_info["cr_str"],
                "c_write": p_info["cw_str"],
                "tier": p_info["tier"],
                "max_credit": p_info["max_credit"],
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
        print(
            "| Modelo (contexto) | Provider | Input | Output | Cache Read | Cache Write | Cost | Score |"
        )
        print("| :--- | :--- | ---: | ---: | ---: | ---: | :--- | ---: |")
    else:
        print(
            "| Modelo (contexto) | Input | Output | Cache Read | Cache Write | Cost | Score |"
        )
        print("| :--- | ---: | ---: | ---: | ---: | :--- | ---: |")

    for r in rows:
        icon = winner_icons.get(r["key"])
        clean_score = r["score_str"].strip("`")
        if show_provider_col:
            if icon:
                print(
                    f"| **{icon} {r['label']}** | **{r['provider_str']}** | **{r['inp']}** | **{r['out']}** | **{r['c_read']}** | **{r['c_write']}** | **{r['tier']}** | **{clean_score}** |"
                )
            elif r["key"] in runner_up_keys:
                print(
                    f"| `{r['label']}` | `{r['provider_str']}` | `{r['inp']}` | `{r['out']}` | `{r['c_read']}` | `{r['c_write']}` | `{r['tier']}` | `{clean_score}` |"
                )
            else:
                print(
                    f"| {r['label']} | {r['provider_str']} | {r['inp']} | {r['out']} | {r['c_read']} | {r['c_write']} | {r['tier']} | {r['score_str']} |"
                )
        else:
            if icon:
                print(
                    f"| **{icon} {r['label']}** | **{r['inp']}** | **{r['out']}** | **{r['c_read']}** | **{r['c_write']}** | **{r['tier']}** | **{clean_score}** |"
                )
            elif r["key"] in runner_up_keys:
                print(
                    f"| `{r['label']}` | `{r['inp']}` | `{r['out']}` | `{r['c_read']}` | `{r['c_write']}` | `{r['tier']}` | `{clean_score}` |"
                )
            else:
                print(
                    f"| {r['label']} | {r['inp']} | {r['out']} | {r['c_read']} | {r['c_write']} | {r['tier']} | {r['score_str']} |"
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
