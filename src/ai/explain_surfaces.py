"""Builds the explain-surfaces prompt and calls Gemini."""
from __future__ import annotations

from src.ai.client import generate
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

    lines = [
        f"User level: {level}",
        f"Ticker: {ticker}  |  Option type: {option_type}",
        "",
        "Note: put_skew measures the IV premium at lower strikes (left tail of the"
        " distribution), regardless of option type. deep_itm_bias is the mean"
        f" signed divergence for {option_type}s at moneyness < 0.80.",
        "",
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
    )
