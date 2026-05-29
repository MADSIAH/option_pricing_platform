"""Builds the explain-surfaces prompt and calls Gemini."""
from __future__ import annotations

from src.ai.client import generate, MODEL_SURFACES
from src.ai.prompts import EXPLAIN_SURFACES_SYSTEM_PROMPT

_LEVEL_LABELS = {
    "beginner": "Beginner",
    "finance_student": "Finance Student",
    "professional": "Professional",
}


def build_surface_explain_message(data: dict) -> str:
    level = _LEVEL_LABELS.get(data["user_level"], data["user_level"])
    ticker = data["ticker"]
    option_type = data["option_type"]

    if data["deep_itm_bias"] is not None:
        deep_itm_line = f"  deep_itm_bias        : {data['deep_itm_bias']:.4f}"
    else:
        deep_itm_line = "  deep_itm_bias        : n/a (no contracts with moneyness < 0.80)"

    # --- Market context block (only include fields present in the payload) ---
    ctx_lines = []
    if data.get("pricing_model"):
        ctx_lines.append(f"  Pricing model      : {data['pricing_model']}")
    if data.get("spot_price") is not None:
        ctx_lines.append(f"  Spot price         : {data['spot_price']:.2f}")
    if data.get("risk_free_rate") is not None:
        ctx_lines.append(f"  Risk-free rate     : {data['risk_free_rate']*100:.2f}%")
    if data.get("dividend_yield") is not None:
        div_flag = "yes" if data.get("has_dividend") else "no"
        ctx_lines.append(f"  Dividend yield     : {data['dividend_yield']*100:.2f}%  ({div_flag})")
    if data.get("atm_iv") is not None:
        ctx_lines.append(f"  ATM implied vol    : {data['atm_iv']*100:.2f}%")
    if data.get("vol_used") is not None:
        src = data.get("vol_source", "")
        ctx_lines.append(f"  Vol (price surface): {data['vol_used']*100:.2f}%  [{src}]")
    if data.get("surface_date"):
        ctx_lines.append(f"  Surface date       : {data['surface_date'][:10]}")

    lines = [
        f"User level: {level}",
        f"Ticker: {ticker}  |  Option type: {option_type}",
        "",
        "Note: put_skew measures the IV premium at lower strikes (left tail of the"
        " distribution), regardless of option type. deep_itm_bias is the mean"
        f" signed divergence for {option_type}s at moneyness < 0.80.",
        "",
        *( ["MARKET CONTEXT", *ctx_lines, ""] if ctx_lines else [] ),
        "VOL SURFACE SCALARS",
        f"  smile_intensity : {data['smile_intensity']:.4f}",
        f"  put_skew        : {data['put_skew']:.4f}",
        "",
        "PRICE SURFACE SCALARS",
        deep_itm_line,
        f"  divergence_threshold : {data['divergence_threshold']:.4f}  (mean|div| + 2*std across all contracts)",
        "",
        "PER-BUCKET METRICS  (T x moneyness grid)",
        f"{'T':12s}  {'Moneyness':12s}  {'spikes':>6}  {'mean_sdiv':>10}  {'mean_adiv':>10}  {'pct_ldiv':>9}  {'n_ldiv':>6}  {'volume':>8}  {'OI':>8}",
        "-" * 110,
    ]

    for b in data["buckets"]:
        def fmt(v, fmt_str):
            return format(v, fmt_str) if v is not None else "       n/a"

        lines.append(
            f"{b['t_label']:12s}  {b['m_label']:12s}  "
            f"{b['spike_count']:>6d}  "
            f"{fmt(b['mean_signed_div'], '>+10.4f')}  "
            f"{fmt(b['mean_abs_div'],    '>10.4f')}  "
            f"{fmt(b['pct_large_div'],   '>9.1%')}  "
            f"{b['count_large_div']:>6d}  "
            f"{b['volume']:>8d}  "
            f"{b['open_interest']:>8d}"
        )

    lines.append("")
    lines.append("Please analyse these surfaces.")
    return "\n".join(lines)


def call_explain_surfaces(data: dict) -> str:
    message = build_surface_explain_message(data)
    return generate(
        EXPLAIN_SURFACES_SYSTEM_PROMPT,
        [{"role": "user", "parts": [{"text": message}]}],
        model=MODEL_SURFACES,
    )
