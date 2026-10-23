"""Market-price data providers.

A provider's only job is to return a pandas DataFrame in the documented CSV format
(see docs/DATA_IMPORT.md). Validation and database writes are handled centrally by
``services.importer`` so every source is held to the same rules.

To add a new source (for example a licensed Agmarknet / data.gov.in API client):

    class DataGovInProvider(PriceProvider):
        name = "data.gov.in"
        is_demo = False
        def __init__(self, api_key: str, resource_id: str): ...
        def fetch(self) -> pd.DataFrame:
            # call the API, map its fields onto STANDARD_COLUMNS, return the frame
            ...

then register it in PROVIDERS. No provider here contacts the network: no API key is
bundled and nothing is scraped.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

STANDARD_COLUMNS = ["state", "district", "market", "commodity", "category", "unit",
                    "arrival_date", "min_price", "max_price", "modal_price", "source"]


class PriceProvider(ABC):
    name: str = "provider"
    is_demo: bool = False

    @abstractmethod
    def fetch(self) -> pd.DataFrame:
        """Return raw rows using STANDARD_COLUMNS (category/unit/source optional)."""


class CsvFileProvider(PriceProvider):
    name = "csv"

    def __init__(self, path, is_demo: bool = False, default_source: str | None = None):
        self.path = Path(path)
        self.is_demo = is_demo
        self.default_source = default_source or f"CSV import: {self.path.name}"

    def fetch(self) -> pd.DataFrame:
        if not self.path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.path}")
        df = pd.read_csv(self.path, dtype=str, keep_default_na=True)
        df.columns = [c.strip().lower() for c in df.columns]
        if "source" not in df.columns:
            df["source"] = self.default_source
        df["source"] = df["source"].fillna(self.default_source)
        return df


PROVIDERS = {"csv": CsvFileProvider}
