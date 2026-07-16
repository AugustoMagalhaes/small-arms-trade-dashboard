# Small Arms Trade Dashboard

Interactive dashboard for Brazil's firearms foreign trade data (2020–2026).
Data source: Comex Stat / MDIC (`dados_small_arms.xlsx`).

## Setup

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Run locally

```bash
python script.py
```

Access **http://127.0.0.1:8050**

## Generate static version

```bash
python script.py --export
```

This generates a static `docs/index.html` that can be accessed without needing to run the Python code again.