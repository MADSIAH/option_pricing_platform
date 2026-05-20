const BASE = 'http://127.0.0.1:8000/api/v1'

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
