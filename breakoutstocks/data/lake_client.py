"""Data Lake Client for accessing market data parquet files."""

import os
from typing import List, Optional
import pandas as pd

from breakoutstocks.config import Config


class DataLakeClient:
    """Client for reading daily, weekly, sector bars and metadata from market data lake.

    Supports reading from local directory or remote GitHub raw URLs.
    """

    DAILY_BARS_FILE = "DailyBars.parquet"
    WEEKLY_BARS_FILE = "WeeklyBars.parquet"
    SECTOR_BARS_FILE = "SectorDailyBars.parquet"
    METADATA_FILE = "StockMetadatas.parquet"

    def __init__(self, local_path: Optional[str] = None):
        """Initialize data lake client with optional local path override."""
        if local_path:
            self.base_path = local_path
        elif Config.LAKE_PATH:
            self.base_path = Config.LAKE_PATH
        else:
            self.base_path = Config.LAKE_GITHUB_URL

        self._daily_bars: Optional[pd.DataFrame] = None
        self._weekly_bars: Optional[pd.DataFrame] = None
        self._sector_daily_bars: Optional[pd.DataFrame] = None
        self._stock_metadata: Optional[pd.DataFrame] = None

    def _load_parquet(self, filename: str) -> Optional[pd.DataFrame]:
        """Load parquet file from local path or URL."""
        if self.base_path.startswith(("http://", "https://")):
            target = f"{self.base_path.rstrip('/')}/{filename}"
        else:
            target = os.path.join(self.base_path, filename)

        try:
            df = pd.read_parquet(target)
            return df
        except Exception:
            return None

    def get_daily_bars(self, symbol: str, days: int = 180) -> Optional[pd.DataFrame]:
        """Get daily bars for a symbol sorted by date ascending.

        Args:
            symbol: Ticker symbol (e.g. 'TCS.NS')
            days: Number of recent daily bars to return

        Returns:
            pd.DataFrame or None if symbol not found or lake unavailable
        """
        if self._daily_bars is None:
            self._daily_bars = self._load_parquet(self.DAILY_BARS_FILE)

        if self._daily_bars is None or self._daily_bars.empty:
            return None

        if "Ticker" not in self._daily_bars.columns:
            return None

        symbol_clean = str(symbol).strip()
        filtered = self._daily_bars[
            self._daily_bars["Ticker"].astype(str).str.upper() == symbol_clean.upper()
        ]

        if filtered.empty:
            return None

        df = filtered.copy()
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.sort_values("Date")

        if days is not None and days > 0:
            df = df.tail(days)

        return df

    def get_weekly_bars(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get weekly bars for a symbol sorted by date ascending.

        Args:
            symbol: Ticker symbol (e.g. 'TCS.NS')

        Returns:
            pd.DataFrame or None if symbol not found or lake unavailable
        """
        if self._weekly_bars is None:
            self._weekly_bars = self._load_parquet(self.WEEKLY_BARS_FILE)

        if self._weekly_bars is None or self._weekly_bars.empty:
            return None

        if "Ticker" not in self._weekly_bars.columns:
            return None

        symbol_clean = str(symbol).strip()
        filtered = self._weekly_bars[
            self._weekly_bars["Ticker"].astype(str).str.upper() == symbol_clean.upper()
        ]

        if filtered.empty:
            return None

        df = filtered.copy()
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.sort_values("Date")

        return df

    def get_stock_metadata(self) -> Optional[pd.DataFrame]:
        """Get stock metadata containing Ticker, Name, and Sector information.

        Returns:
            pd.DataFrame or None if metadata unavailable
        """
        if self._stock_metadata is None:
            self._stock_metadata = self._load_parquet(self.METADATA_FILE)

        if self._stock_metadata is None or self._stock_metadata.empty:
            return None

        return self._stock_metadata.copy()

    def get_sector_index(self, index: str, days: int = 30) -> Optional[pd.DataFrame]:
        """Get sector index daily bars sorted by date ascending.

        Args:
            index: Sector index name or ticker (e.g. 'NIFTY_IT')
            days: Number of recent daily bars to return

        Returns:
            pd.DataFrame or None if index not found or lake unavailable
        """
        if self._sector_daily_bars is None:
            self._sector_daily_bars = self._load_parquet(self.SECTOR_BARS_FILE)

        if self._sector_daily_bars is None or self._sector_daily_bars.empty:
            return None

        index_clean = str(index).strip().upper()
        df_sector = self._sector_daily_bars

        mask = pd.Series(False, index=df_sector.index)
        if "Ticker" in df_sector.columns:
            mask = mask | (df_sector["Ticker"].astype(str).str.upper() == index_clean)
        if "Sector" in df_sector.columns:
            mask = mask | (df_sector["Sector"].astype(str).str.upper() == index_clean)

        filtered = df_sector[mask]
        if filtered.empty:
            return None

        df = filtered.copy()
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.sort_values("Date")

        if days is not None and days > 0:
            df = df.tail(days)

        return df

    def get_all_tickers(self) -> List[str]:
        """Get list of all available stock ticker symbols.

        Returns:
            List of ticker strings
        """
        meta = self.get_stock_metadata()
        if meta is not None and not meta.empty and "Ticker" in meta.columns:
            return [str(t) for t in meta["Ticker"].dropna().unique()]

        # Fallback to DailyBars if metadata is not available
        if self._daily_bars is None:
            self._daily_bars = self._load_parquet(self.DAILY_BARS_FILE)

        if self._daily_bars is not None and not self._daily_bars.empty and "Ticker" in self._daily_bars.columns:
            return [str(t) for t in self._daily_bars["Ticker"].dropna().unique()]

        return []

    def get_stock_name(self, symbol: str) -> str:
        """Get human-readable company name for a given ticker symbol.

        Args:
            symbol: Ticker symbol

        Returns:
            Company name string or fallback to symbol if not found
        """
        meta = self.get_stock_metadata()
        if meta is not None and not meta.empty and "Ticker" in meta.columns and "Name" in meta.columns:
            symbol_clean = str(symbol).strip().upper()
            matched = meta[meta["Ticker"].astype(str).str.upper() == symbol_clean]
            if not matched.empty:
                val = matched.iloc[0]["Name"]
                if pd.notna(val):
                    return str(val)

        return str(symbol)
