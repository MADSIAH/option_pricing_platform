# User Guide — OptionDesk

**Live app:** https://option-pricing-platform.vercel.app/

OptionDesk is a web-based option pricing platform for educational purposes. It prices European and American options using multiple models, computes the full set of Greeks, and visualises the implied volatility surface from live market data.

---

## Interface Overview

The app has two main tabs:

| Tab | What it shows |
|-----|---------------|
| **Pricing & Greeks** | Input panel + prices for all models + Greeks + AI explanation + sensitivity chart |
| **Surfaces** | Implied volatility surface + model price surface across strikes and maturities |

The **NavBar** (top bar) always shows the current risk-free rate, implied volatility, and — when a ticker is selected — the live spot price and ticker symbol. A **Light/Dark** toggle is available top-right.

---

## Pricing & Greeks

### Step 1 — Choose a stock

In the **Parameters** panel on the left, select one of the pre-loaded tickers:

| Ticker | Description |
|--------|-------------|
| **AAPL** | Apple Inc. |
| **SPY** | S&P 500 ETF |
| **TSLA** | Tesla Inc. |

Click a ticker button: the app fetches the live spot price, risk-free rate (US 3-Month T-Bill via FRED), ATM implied volatility, and dividend yield automatically. All fields are still editable after loading.

Click **Other** to enter parameters manually (spot price and volatility must be typed in).

### Step 2 — Set the contract parameters

| Field | Symbol | Description |
|-------|--------|-------------|
| Underlying Price | S | Spot price of the stock (pre-filled from market data) |
| Strike Price | K | Exercise price of the option |
| Time to Maturity | T | Days until expiry; shown in years below the field |
| Risk-Free Rate | r | Annualised continuously compounded rate (%) |
| Volatility | σ | Annualised volatility (%) |

A **moneyness badge** (ATM / ITM / OTM) appears top-right of the panel as you type.

**Volatility toggle (IV / HV):** when a ticker is selected, switch between implied volatility (from the option chain) and historical volatility (30-day realised vol) using the small toggle next to the σ field.

**Advanced — Dividend Yield (q):** expand the *Advanced* section at the bottom of the panel to set a continuous dividend yield (%). Defaults to 0 for non-dividend-paying stocks.

### Step 3 — Choose option style and pricing method

**Style:**

| Style | Description |
|-------|-------------|
| **European** | Can only be exercised at expiry |
| **American** | Can be exercised at any time before expiry |

**Method (European):**

| Method | Description |
|--------|-------------|
| Black-Scholes | Closed-form analytical solution — fastest, exact |
| Monte Carlo | GBM path simulation with antithetic variates (50 000 paths) |
| Binomial Tree | CRR lattice with 500 steps |

**Method (American):**

| Method | Description |
|--------|-------------|
| BAW | Barone-Adesi & Whaley analytical approximation — very fast |
| Longstaff-Schwartz | Monte Carlo regression (LSM) — most accurate for American options |
| Binomial Tree | CRR lattice, supports early exercise at every node |

### Step 4 — Read the results

Results update automatically (500 ms debounce) whenever any input changes.

**Price Display** shows:
- Call and put prices for the selected method
- A comparison table with prices from all available methods side by side

**Greeks Grid** shows the five standard Greeks for both call and put:

| Greek | Symbol | Meaning |
|-------|--------|---------|
| Delta | Δ | Price sensitivity to spot price (∂V/∂S) |
| Gamma | Γ | Rate of change of delta (∂²V/∂S²) |
| Vega | ν | Sensitivity to volatility (∂V/∂σ) |
| Theta | Θ | Time decay (∂V/∂T, per day) |
| Rho | ρ | Sensitivity to risk-free rate (∂V/∂r) |

**Sensitivity Chart** (European options only): plots call and put prices across a ±45% spot price range around the current spot, with vertical lines marking the current spot (S) and strike (K).

### Step 5 — AI Explanation

After prices are computed, an **AI Explanation** panel appears below the Greeks. Select your experience level:

- **Beginner** — plain language, no jargon
- **Student** — includes model mechanics and formula intuition
- **Professional** — concise, quantitative, practitioner-level

Click **Explain these results** to generate a Gemini-powered explanation of the current pricing output. The explanation covers what the price means, what the Greeks imply, and relevant caveats.

> Note: this feature requires the backend to be online. The response is for educational purposes only and does not constitute investment advice.

### Ask AI (chat)

Click **Ask AI** in the top-right of the NavBar to open a floating chat panel. Ask any question about options, pricing models, or Greeks — the assistant is context-aware and adapts its answers to the selected experience level.

---

## Surfaces

Switch to the **Surfaces** tab for two interactive 3D plots.

### Implied Volatility Surface

Displays the implied volatility extracted from the live option chain for the selected ticker, plotted across:
- **X axis** — strike price (K)
- **Y axis** — time to maturity (T, in years)
- **Z axis** — implied volatility (σ_IV, %)

This surface shows the volatility smile/skew: how market-implied vol varies with moneyness and maturity. Select **Call** or **Put** using the toggle.

> Requires a ticker to be selected. Only available for AAPL, SPY, and TSLA.

### Price Surface

Compares model prices against market mid-prices across a grid of strikes and maturities for the selected ticker. Useful for identifying where a model over- or under-prices relative to the market.

---

## Tips

- **No ticker selected?** You can still price options manually — just type in S, K, T, r, and σ. The vol surface will not be available.
- **Stale data warning:** if market data is older than 15 minutes, a yellow "stale" indicator appears next to the spot price.
- **American call:** on a non-dividend-paying stock, the early exercise premium is zero — American and European call prices will be identical. This is expected.
- **Results are instant for BS/BAW, slower for MC/LS:** Monte Carlo and Longstaff-Schwartz run fewer paths (5 000) in American mode to keep response times reasonable.

---

## Limitations

- **Educational only** — prices are indicative and should not be used for trading decisions.
- **Market data delays** — Yahoo Finance data may be delayed by 15 minutes during market hours.
- **Backend required** — AI explanation, chat, market data fetch, and vol surface all depend on the backend API being online.
