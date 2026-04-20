# AI-Enhanced Options Pricing Platform

> Programming in Finance II - Big Projects 2026
> Project 2.7 - Universita della Svizzera italiana (USI)

An AI-enhanced platform for advanced options pricing, volatility surface modeling, Greeks analysis, and interactive financial visualization.

## Project Status

This repository currently documents the project scope, requirements, and planned architecture for the platform. The implementation roadmap starts with European options priced with Black-Scholes for benchmarking, then expands to advanced numerical pricing, volatility modeling, real-time data ingestion, and AI-assisted explanations.

## Project Idea

We are developing an options pricing platform that combines quantitative finance, software engineering, visualization, and AI. The goal is to create an interactive and accessible tool that computes theoretical option prices, calculates the full set of Greeks, models the volatility surface, and explains the results in a way that matches the user's background.

The platform is designed to support:

- students learning derivatives pricing
- finance practitioners validating option values and sensitivities
- users who want intuitive dashboards and AI-guided explanations

## Problem Definition

Option pricing depends on several variables: spot price, strike, maturity, volatility, and interest rates. Understanding how these drivers interact is not always straightforward, especially when moving beyond closed-form models. This project addresses that problem by building a platform that:

- computes option prices with advanced numerical methods
- calculates all main Greeks
- visualizes volatility across strikes and maturities
- integrates live market and macroeconomic data
- explains pricing results in natural language

## Minimum Requirements

The platform must:

- build a platform for advanced options pricing
- implement volatility surface modeling
- calculate all main Greeks: Delta, Gamma, Vega, Theta, and Rho
- price options with at least one advanced method such as Monte Carlo simulations, binomial trees, or FFT-based pricing

## Nice to Have

Stretch goals for the platform include:

- use an LLM to explain pricing results and risk exposures
- implement a web dashboard with strong user experience
- visualize the volatility surface interactively
- support mobile-friendly usage
- extend the platform toward American options and crypto options

## Main Objectives

This project aims to:

- compute option prices with advanced numerical methods
- benchmark European options with the Black-Scholes model
- calculate the main Greeks for every pricing result
- model and visualize the volatility surface
- integrate real-time market data for pricing inputs
- build a web frontend with a strong focus on UX
- create interactive dashboards with AI insights
- expose functionality through a custom API with rate limiting
- add an LLM-based explanation module for finance concepts and model outputs

## Financial Scope

The implementation roadmap starts with:

- European call and put options
- Black-Scholes pricing as the baseline analytical model
- optimization and parameter analysis around European options

The project will then expand toward:

- Monte Carlo pricing
- Binomial Tree pricing
- American options
- possible crypto option support

## Chosen Pricing Methods

The main advanced methods planned for the pricing engine are:

- Monte Carlo simulation
- Binomial Tree methods

These methods were chosen because they are advanced enough to satisfy the project requirements while remaining interpretable and suitable for educational use. Black-Scholes will be used as the baseline reference for European options.

## Planned Features

### Option Pricing Module

- Price options using Black-Scholes for European contracts
- Add advanced pricing with Monte Carlo and Binomial Tree methods
- Compare advanced-method results against theoretical Black-Scholes benchmarks where applicable

### Greeks Module

- Compute Delta
- Compute Gamma
- Compute Vega
- Compute Theta
- Compute Rho

### Volatility Surface Module

- Build the implied volatility surface from market option chains
- Visualize the surface across strike and maturity dimensions
- Support interactive exploration through the frontend

### Real-Time Data Module

- Fetch equity and option data with `yfinance`
- Fetch risk-free rate data with the FRED API
- Schedule automatic updates with `APScheduler`
- Refresh data every 10 to 60 minutes depending on configuration

### Web Frontend

- Provide a clean and user-friendly web interface
- Support desktop and mobile-friendly usage
- Focus on clear workflows for pricing, Greeks, and volatility analysis
- Add advanced charts and interactive dashboards

### AI and LLM Support

- Explain pricing outputs in natural language
- Adapt explanations to the user's knowledge level
- Support profiles such as `noob`, `finance student`, and `professional trader`
- Help users understand parameters, model assumptions, and risk sensitivities

### API Layer

- Expose pricing and volatility functionality through our own API
- Add rate limiting as the first planned protection mechanism
- Keep the architecture ready for future authentication if needed

## User Experience Vision

The platform should not only be technically correct but also easy to use. The UX goals are:

- simple pricing workflows
- responsive dashboards
- clear risk visualization
- accessible explanations for different experience levels
- smooth use on both web and mobile screens

## AI-Assisted Explanations

One key differentiator of the project is the explanation layer. When a user asks for clarification, the assistant can first identify the user's background and then explain the option parameters and pricing results accordingly.

Examples:

- `noob`: simple language and intuition-first explanations
- `finance student`: more mathematical detail and terminology
- `professional trader`: concise, market-oriented interpretation

As a further extension, we may explore a trading assistant that adapts to user needs, budget, and risk tolerance.

## Technical Structure

The project is planned as a modular platform with separate components for:

- pricing engine
- Greeks computation
- volatility surface construction and visualization
- real-time data ingestion
- API services
- frontend application
- LLM explanation module

This modular structure will make the platform easier to build, test, and extend.

## Proposed Repository Structure

```text
option_pricing_platform/
|-- README.md
|-- AGENTS.md
|-- requirements.txt
|-- .env.example
|
|-- core/
|   |-- black_scholes.py
|   |-- monte_carlo.py
|   |-- binomial_tree.py
|   |-- greeks.py
|   `-- volatility_surface.py
|
|-- data/
|   |-- market_data.py
|   |-- fred_rates.py
|   `-- scheduler.py
|
|-- api/
|   |-- main.py
|   |-- routes/
|   `-- rate_limits.py
|
|-- frontend/
|   |-- app.py
|   `-- components/
|
|-- llm/
|   |-- explainer.py
|   `-- prompts/
|
`-- tests/
    |-- test_pricing.py
    |-- test_greeks.py
    `-- test_api.py
```

## Project Roadmap

### Phase 1

- Set up repository structure
- Implement European options with Black-Scholes
- Compute all Greeks
- Build baseline tests

### Phase 2

- Add Monte Carlo and Binomial Tree pricing
- Build volatility surface workflows
- Add data ingestion with `yfinance` and FRED

### Phase 3

- Create the web dashboard
- Add interactive charts and dashboards
- Integrate the LLM explanation module

### Phase 4

- Expose a public-facing API with rate limiting
- Improve mobile UX
- Explore American options and crypto extensions

## Expected Result

At the end of the project, we expect to have a working platform that:

- prices options using live or frequently refreshed market data
- computes Greeks for all supported models
- visualizes the volatility surface
- provides AI-supported explanations
- offers an interactive web application with strong usability

## GitHub and AI Contribution

The project will be developed on GitHub with regular commits, documentation updates, and at least one AI-supported pull request. The repository will include an `AGENTS.md` file describing how AI tools contribute to the workflow, in line with the course requirements.

## Conclusion

This project combines finance, programming, data engineering, AI, and visualization in one platform. The aim is to deliver a technically solid and well-documented solution that is both rigorous and easy to use.
