// Black-Scholes-Merton pricing with dividend yield (q), matching src/pricing exactly.
// d1 = (ln(S/K) + (r - q + 0.5*sigma^2)*T) / (sigma*sqrt(T))
// d2 = d1 - sigma*sqrt(T)

const SQRT2 = Math.SQRT2
const SQRT_2PI = Math.sqrt(2 * Math.PI)

function erf(x) {
  const t = 1.0 / (1.0 + 0.3275911 * Math.abs(x))
  const poly =
    t * (0.254829592 + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429))))
  const y = 1.0 - poly * Math.exp(-x * x)
  return x < 0 ? -y : y
}

const normCDF = (x) => 0.5 * (1.0 + erf(x / SQRT2))
const normPDF = (x) => Math.exp(-0.5 * x * x) / SQRT_2PI

function calcD1(S, K, T, r, sigma, q) {
  return (Math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / (sigma * Math.sqrt(T))
}

/**
 * Compute BSM prices and all five analytical Greeks for both call and put.
 * S, K, T (years), r, sigma, q are all plain decimals (e.g. 0.20 for 20%).
 * Returns null if any input is invalid.
 */
export function compute(S, K, T, r, sigma, q = 0) {
  if (!S || !K || !T || !sigma || S <= 0 || K <= 0 || T <= 0 || sigma <= 0 || q < 0) return null

  const sqrtT = Math.sqrt(T)
  const d1 = calcD1(S, K, T, r, sigma, q)
  const d2 = d1 - sigma * sqrtT
  const discR = Math.exp(-r * T)
  const discQ = Math.exp(-q * T)
  const nd1 = normPDF(d1)
  const Nd1 = normCDF(d1)
  const Nd2 = normCDF(d2)
  const Nnd1 = normCDF(-d1)
  const Nnd2 = normCDF(-d2)

  const callPrice = S * discQ * Nd1 - K * discR * Nd2
  const putPrice = K * discR * Nnd2 - S * discQ * Nnd1

  const gamma = (discQ * nd1) / (S * sigma * sqrtT)
  const vega = (S * discQ * nd1 * sqrtT) / 100 // per 1% vol move

  const callDelta = discQ * Nd1
  const putDelta = discQ * (Nd1 - 1)

  const callTheta =
    (-(S * sigma * discQ * nd1) / (2 * sqrtT) - r * K * discR * Nd2 + q * S * discQ * Nd1) / 365
  const putTheta =
    (-(S * sigma * discQ * nd1) / (2 * sqrtT) + r * K * discR * Nnd2 - q * S * discQ * Nnd1) / 365

  const callRho = (K * T * discR * Nd2) / 100 // per 1% rate move
  const putRho = (-K * T * discR * Nnd2) / 100

  return {
    call: { price: callPrice, delta: callDelta, gamma, vega, theta: callTheta, rho: callRho },
    put: { price: putPrice, delta: putDelta, gamma, vega, theta: putTheta, rho: putRho },
    d1,
    d2,
    putCallParity: S * discQ - K * discR,
  }
}

/**
 * Compute call and put prices across a range of spot prices for the sensitivity chart.
 */
export function computeRange(K, T, r, sigma, q, sMin, sMax, points = 120) {
  const step = (sMax - sMin) / (points - 1)
  const spots = []
  const calls = []
  const puts = []

  for (let i = 0; i < points; i++) {
    const S = sMin + i * step
    spots.push(S)
    const res = compute(S, K, T, r, sigma, q)
    calls.push(res ? res.call.price : Math.max(S - K, 0))
    puts.push(res ? res.put.price : Math.max(K - S, 0))
  }

  return { spots, calls, puts }
}
