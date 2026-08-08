# Task 1: Project Scaffolding, Config, and Models

## Files
- Create: `requirements.txt`
- Create: `breakoutstocks/__init__.py`
- Create: `breakoutstocks/config.py`
- Create: `breakoutstocks/models/__init__.py`
- Create: `breakoutstocks/models/types.py`
- Create: `breakoutstocks/utils/__init__.py`
- Create: `breakoutstocks/utils/logging.py`
- Create: `breakoutstocks/data/__init__.py`
- Create: `breakoutstocks/indicators/__init__.py`
- Create: `breakoutstocks/scanners/__init__.py`
- Create: `tests/__init__.py`
- Modify: `.gitignore`
- Create: `output/.gitkeep`

## Interfaces
- Produces: `Config` dataclass, `Advice` enum, `Confidence` enum, `TradePlan` dataclass, `StockAnalysis` dataclass, `ScanResult` dataclass, `MarketRegime` dataclass, `setup_logging()` function

## Global Constraints
- Python 3.10+ required
- All configuration constants in ONE file: `breakoutstocks/config.py` — no magic numbers in logic
- Data lake URL: `https://raw.githubusercontent.com/ubermachine/market-data-lake/main/data`
- NSE option chain endpoint: `https://www.nseindia.com/api/option-chain-equities?symbol={symbol}`
- NSE FII/DII endpoint: `https://www.nseindia.com/api/fiidiiTradeReact`
- Commit after task completes

## Steps
1. Create `requirements.txt` with:
```
streamlit>=1.28.0
pandas>=2.0.0
numpy>=1.24.0
yfinance>=0.2.28
plotly>=5.15.0
pyarrow>=12.0.0
requests>=2.31.0
pytest>=7.4.0
```
2. Create package `__init__.py` files for `breakoutstocks`, `breakoutstocks/models`, `breakoutstocks/data`, `breakoutstocks/indicators`, `breakoutstocks/scanners`, `breakoutstocks/utils`, `tests`.
3. Create `breakoutstocks/utils/logging.py` with `setup_logging()`.
4. Create `breakoutstocks/config.py` with `Config` dataclass containing all thresholds and endpoints.
5. Create `breakoutstocks/models/types.py` with `Advice`, `Confidence`, `TradePlan`, `StockAnalysis`, `ScanResult`, `MarketRegime`.
6. Update `.gitignore` to ignore `output/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`.
7. Create `output/.gitkeep`.
8. Verify imports work: `python -c "from breakoutstocks.config import Config; from breakoutstocks.models.types import Advice; from breakoutstocks.utils.logging import setup_logging; print('Scaffolding OK')"`
9. Commit with `git add -A` and `git commit -m "feat: scaffold package structure, config, models, and logging"`
