"""Base scanner abstract base class with parallel execution pattern."""

import logging
import os
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Callable, Dict, List, Optional

import pandas as pd

from breakoutstocks.config import Config
from breakoutstocks.data.client import MarketDataClient

logger = logging.getLogger(__name__)


class BaseScanner(ABC):
    """Abstract Base Class for stock scanners with ThreadPoolExecutor parallel execution."""

    def __init__(
        self,
        data_client: Optional[MarketDataClient] = None,
        config: Optional[Config] = None,
    ):
        """Initialize BaseScanner.

        Args:
            data_client: Optional MarketDataClient instance.
            config: Optional Config instance.
        """
        self.config = config or (data_client.config if data_client else Config())
        self.data = data_client or MarketDataClient(config=self.config)
        self.logger = logging.getLogger(self.__class__.__name__)

    def scan(
        self,
        symbols: List[str],
        max_workers: int = 10,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> pd.DataFrame:
        """Run parallel stock analysis using ThreadPoolExecutor.

        Args:
            symbols: List of stock symbols to scan.
            max_workers: Max worker threads for execution.
            progress_callback: Optional callback receiving (completed, total).

        Returns:
            pd.DataFrame of scan results.
        """
        if not symbols:
            return pd.DataFrame()

        results: List[Dict] = []
        total = len(symbols)
        completed = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_symbol = {
                executor.submit(self.analyze_stock, symbol): symbol for symbol in symbols
            }

            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    res = future.result()
                    if res is not None:
                        results.append(res)
                except Exception as err:
                    self.logger.warning(f"Error scanning symbol {symbol}: {err}")

                completed += 1
                if progress_callback:
                    try:
                        progress_callback(completed, total)
                    except Exception as cb_err:
                        self.logger.debug(f"Progress callback error: {cb_err}")

        if not results:
            return pd.DataFrame()

        df = pd.DataFrame(results)
        if "strength_score" in df.columns:
            df = df.sort_values(by="strength_score", ascending=False).reset_index(drop=True)
        return df

    @abstractmethod
    def analyze_stock(self, symbol: str) -> Optional[Dict]:
        """Analyze a single stock symbol. Must be implemented by subclasses.

        Args:
            symbol: Ticker symbol to analyze.

        Returns:
            Dictionary of analysis results or None if no signal / invalid data.
        """
        pass

    def save_results(self, df: pd.DataFrame, prefix: str) -> str:
        """Save results DataFrame to a timestamped CSV file in config.OUTPUT_DIR.

        Args:
            df: DataFrame of scan results.
            prefix: Prefix for output CSV filename.

        Returns:
            Saved CSV file path as string.
        """
        output_dir = getattr(self.config, "OUTPUT_DIR", "output")
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.csv"
        filepath = os.path.join(output_dir, filename)

        if df is not None and not df.empty:
            df.to_csv(filepath, index=False)
        else:
            pd.DataFrame().to_csv(filepath, index=False)

        return filepath
