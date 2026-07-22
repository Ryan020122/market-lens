# Market Lens

A macro-first financial information dashboard built for learning how buy-side investors process information.

## Included

- Cross-asset morning brief
- Central-bank snapshot
- FRED macro charts
- GDELT global news search
- Headline-to-transmission-channel classification
- Learning library for rates, yield curves, FX, credit spreads, inflation, cash flow and CapEx
- Shock-transmission exercises and quiz
- Optional watchlist and position log
- Research notebook with disconfirming-evidence prompts

## Run locally

1. Install Python 3.11 or 3.12.
2. Open a terminal in this folder.
3. Create and activate an environment:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Optional: copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and add a free FRED API key.
6. Start the app:

```bash
streamlit run streamlit_app.py
```

## Deploy as a website

1. Create a GitHub repository and upload this folder's files.
2. Sign in to Streamlit Community Cloud with GitHub.
3. Click **Create app** and select `streamlit_app.py`.
4. In Advanced settings, optionally add:

```toml
FRED_API_KEY = "your_key"
```

5. Deploy. You will receive a shareable `streamlit.app` URL.

## Data sources

- Yahoo Finance through `yfinance` for market prices
- Federal Reserve Bank of St. Louis FRED API for US macro series
- GDELT DOC 2.0 API for news discovery
- Bank of England and European Central Bank official policy pages

## Limitations

- Yahoo data may be delayed or temporarily unavailable.
- GDELT is a discovery tool; verify the original article.
- Rule-based headline tags are conservative and can be wrong.
- This is an educational research tool, not investment advice.
- Do not store brokerage passwords or sensitive financial credentials in the app.

## Strong next upgrades

- Economic calendar with consensus-versus-actual surprises
- SEC 8-K and 10-Q alerts
- Central-bank statement change detection
- GBP return attribution and portfolio factor exposure
- Source-cited LLM summaries
- Email or Telegram morning brief
