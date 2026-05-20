const BASE = 'http://127.0.0.1:8000/api/v1'

export const WATCHED_TICKERS = ['AAPL', 'SPY', 'TSLA']

export async function fetchMarket(ticker) {
  const res = await fetch(`${BASE}/market/${ticker}`)
  if (!res.ok) throw new Error(`Market fetch failed: ${res.status}`)
  return res.json()
}
