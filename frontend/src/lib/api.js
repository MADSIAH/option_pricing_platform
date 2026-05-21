const BASE = '/api/v1'

export const WATCHED_TICKERS = ['AAPL', 'SPY', 'TSLA']

export async function fetchMarket(ticker) {
  const res = await fetch(`${BASE}/market/${ticker}`)
  if (!res.ok) throw new Error(`Market fetch failed: ${res.status}`)
  return res.json()
}

// Returns risk-free rate as a percentage (e.g. 3.60)
export async function fetchRFR() {
  const data = await fetchMarket('AAPL')
  return +(data.risk_free_rate * 100).toFixed(2)
}

export async function priceOption(payload) {
  const res = await fetch(`${BASE}/price`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || err.error || `Pricing failed: ${res.status}`)
  }
  return res.json()
}
