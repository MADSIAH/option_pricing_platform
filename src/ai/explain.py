"""Builds the explain prompt and calls Gemini for pricing result explanations."""
from __future__ import annotations

from src.ai.client import generate
from src.ai.prompts import EXPLAIN_SYSTEM_PROMPT

_LEVEL_LABELS = {
    "beginner": "Beginner",
    "finance_student": "Finance Student",
    "professional": "Professional",
}


def build_explain_message(data: dict) -> str:
    """Serialise a pricing result dict into a structured user-turn message."""
    level = _LEVEL_LABELS.get(data["user_level"], data["user_level"])

    price_lines = []
    for method, output in data["prices"].items():
        g = output["greeks"]
        price_lines.append(
            f"  {method}:\n"
            f"    price  = {output['price']:.4f}\n"
            f"    delta  = {g['delta']:.4f}\n"
            f"    gamma  = {g['gamma']:.4f}\n"
            f"    vega   = {g['vega']:.4f}\n"
            f"    theta  = {g['theta']:.4f}\n"
            f"    rho    = {g['rho']:.4f}"
        )

    return (
        f"User level: {level}\n\n"
        f"Option parameters:\n"
        f"  Type:              {data['option_type']} ({data['style']})\n"
        f"  Spot price (S):    {data['S']}\n"
        f"  Strike (K):        {data['K']}\n"
        f"  Time to expiry (T):{data['T']:.4f} years\n"
        f"  Risk-free rate (r):{data['r']:.4f}\n"
        f"  Volatility (sigma):{data['sigma']:.4f}\n"
        f"  Dividend yield (q):{data['q']:.4f}\n\n"
        f"Pricing results:\n" + "\n".join(price_lines) + "\n\n"
        f"Active method: {data['method']}\n\n"
        "Please explain these results."
    )


def call_explain(data: dict) -> str:
    """Generate a plain-language explanation for the given pricing result."""
    message = build_explain_message(data)
    return generate(EXPLAIN_SYSTEM_PROMPT, [{"role": "user", "parts": [{"text": message}]}])
