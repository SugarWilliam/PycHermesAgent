"""Multi-source data fetchers with automatic fallback and local cache."""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional, Callable
from urllib.parse import urlparse

import numpy as np
import pandas as pd
import requests

logger = logging.getLogger("metamodel.data")

DEFAULT_CACHE_DIR = Path.home() / ".metamodel" / "cache"


class DataFetcher:
    """
    Robust data fetcher with:
    - Multi-source fallback (primary -> backup -> synthetic)
    - Local disk cache (CSV/Parquet)
    - Auto-retry with exponential backoff
    - Graceful degradation to synthetic data with warnings
    """

    def __init__(self, cache_dir: Optional[Path] = None, timeout: int = 30):
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "MetaModel/4.0 (Academic Research Data Fetcher)"
        })

    def _cache_path(self, key: str, ext: str = "parquet") -> Path:
        return self.cache_dir / f"{key}.{ext}"

    def _load_cache(self, key: str) -> Optional[pd.DataFrame]:
        path = self._cache_path(key, "parquet")
        if path.exists():
            try:
                return pd.read_parquet(path)
            except Exception:
                pass
        path_csv = self._cache_path(key, "csv")
        if path_csv.exists():
            try:
                return pd.read_csv(path_csv)
            except Exception:
                pass
        return None

    def _save_cache(self, key: str, df: pd.DataFrame) -> None:
        try:
            df.to_parquet(self._cache_path(key, "parquet"), index=False)
        except Exception:
            df.to_csv(self._cache_path(key, "csv"), index=False)

    def fetch(
        self,
        primary_url: str,
        backup_urls: Optional[list[str]] = None,
        parser: Optional[Callable[[str], pd.DataFrame]] = None,
        cache_key: Optional[str] = None,
        synthetic_fallback: Optional[Callable[[], pd.DataFrame]] = None,
        retries: int = 3,
    ) -> pd.DataFrame:
        """
        Fetch data with full fallback chain:
        1. Local cache
        2. Primary URL (with retries)
        3. Backup URLs
        4. Synthetic fallback (with loud warning)
        """
        cache_key = cache_key or urlparse(primary_url).path.replace("/", "_")[-50:]

        # 1. Cache
        cached = self._load_cache(cache_key)
        if cached is not None:
            logger.info("Loaded %s from cache", cache_key)
            return cached

        # 2. Primary + backups
        urls = [primary_url] + (backup_urls or [])
        last_error = None
        for url in urls:
            for attempt in range(retries):
                try:
                    resp = self.session.get(url, timeout=self.timeout)
                    if resp.status_code == 200:
                        text = resp.text
                        df = parser(text) if parser else self._default_csv_parser(text)
                        self._save_cache(cache_key, df)
                        logger.info("Fetched %s from %s", cache_key, url)
                        return df
                except Exception as e:
                    last_error = e
                    wait = 2 ** attempt
                    logger.warning("Attempt %d for %s failed: %s. Retrying in %ds...", attempt + 1, url, e, wait)
                    time.sleep(wait)

        # 4. Synthetic fallback
        if synthetic_fallback is not None:
            logger.error("All sources failed for %s. Using synthetic fallback. Error: %s", cache_key, last_error)
            df = synthetic_fallback()
            df.attrs["_synthetic"] = True
            df.attrs["_synthetic_reason"] = str(last_error)
            self._save_cache(cache_key + "_synthetic", df)
            return df

        raise RuntimeError(f"Failed to fetch {cache_key} from all sources. Last error: {last_error}")

    @staticmethod
    def _default_csv_parser(text: str) -> pd.DataFrame:
        from io import StringIO
        return pd.read_csv(StringIO(text))

    # ============== Convenience fetchers for known sources ==============

    def noaa_co2(self) -> pd.DataFrame:
        """NOAA Mauna Loa CO2 monthly. Fallback: Scripps."""
        def _parse_co2(text: str) -> pd.DataFrame:
            lines = text.strip().split("\n")
            records = []
            for line in lines:
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 5:
                    try:
                        val = float(parts[3])
                        if val > 0:
                            records.append({
                                "year": int(parts[0]),
                                "month": int(parts[1]),
                                "decimal_date": float(parts[2]),
                                "co2_ppm": val,
                            })
                    except Exception:
                        pass
            return pd.DataFrame(records)

        def _synthetic_co2() -> pd.DataFrame:
            years = np.arange(1958, 2026)
            months = np.tile(np.arange(1, 13), len(years))[: len(years) * 12]
            co2 = 315 + 1.8 * (np.arange(len(years) * 12) / 12) + 3 * np.sin(np.arange(len(years) * 12) * np.pi / 6)
            return pd.DataFrame({
                "year": np.repeat(years, 12)[:len(co2)],
                "month": months[:len(co2)],
                "decimal_date": np.repeat(years, 12)[:len(co2)] + (months[:len(co2)] - 0.5) / 12,
                "co2_ppm": co2,
            })

        return self.fetch(
            primary_url="https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.txt",
            backup_urls=["https://scrippsco2.ucsd.edu/assets/data/atmospheric/station_in_situ_co2/daily/daily_merge_co2_mlo.txt"],
            parser=_parse_co2,
            cache_key="noaa_co2_monthly",
            synthetic_fallback=_synthetic_co2,
        )

    def world_bank_gdp(self) -> pd.DataFrame:
        """World Bank global GDP (current USD)."""
        def _parse_wb(text: str) -> pd.DataFrame:
            data = json.loads(text)
            records = []
            if len(data) > 1:
                for item in data[1]:
                    if item.get("value") is not None:
                        records.append({"year": int(item["date"]), "gdp_usd": item["value"]})
            return pd.DataFrame(records).sort_values("year")

        def _synthetic_gdp() -> pd.DataFrame:
            years = np.arange(1960, 2025)
            gdp = 1_500e9 * (1.06 ** (years - 1960))  # 6% growth
            return pd.DataFrame({"year": years, "gdp_usd": gdp})

        import json
        return self.fetch(
            primary_url="https://api.worldbank.org/v2/country/WLD/indicator/NY.GDP.MKTP.CD?format=json&per_page=100&date=1960:2024",
            parser=_parse_wb,
            cache_key="wb_gdp_global",
            synthetic_fallback=_synthetic_gdp,
        )

    def jhu_covid(self, country: str = "US") -> pd.DataFrame:
        """JHU CSSE COVID time series for a country."""
        def _parse_jhu(text: str) -> pd.DataFrame:
            df = pd.read_csv(pd.io.common.StringIO(text))
            df = df[df["Country/Region"] == country]
            df = df.drop(columns=["Lat", "Long", "Province/State"], errors="ignore")
            df = df.groupby("Country/Region").sum(numeric_only=True)
            df = df.T
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()
            df.columns = ["cumulative_cases"]
            df["new_cases"] = df["cumulative_cases"].diff().fillna(0).clip(lower=0)
            # 7-day rolling mean + outlier cap
            df["new_cases_smooth"] = df["new_cases"].rolling(7, min_periods=1).mean()
            q99 = df["new_cases_smooth"].quantile(0.99)
            df["new_cases_smooth"] = df["new_cases_smooth"].clip(upper=q99 * 2)
            return df.reset_index().rename(columns={"index": "date"})

        return self.fetch(
            primary_url="https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv",
            parser=_parse_jhu,
            cache_key=f"jhu_covid_{country}",
        )

    def owid_covid(self, iso_code: str = "USA") -> pd.DataFrame:
        """Our World in Data COVID metrics."""
        def _parse_owid(text: str) -> pd.DataFrame:
            df = pd.read_csv(pd.io.common.StringIO(text), usecols=[
                "iso_code", "location", "date", "new_cases", "new_cases_smoothed",
                "stringency_index", "total_cases", "population",
            ])
            df = df[df["iso_code"] == iso_code].copy()
            df["date"] = pd.to_datetime(df["date"])
            return df.sort_values("date").dropna(subset=["new_cases_smoothed"])

        return self.fetch(
            primary_url="https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/owid-covid-data.csv",
            parser=_parse_owid,
            cache_key=f"owid_covid_{iso_code}",
        )

    def gistemp(self) -> pd.DataFrame:
        """NASA GISTEMP global temperature anomaly."""
        def _parse_gistemp(text: str) -> pd.DataFrame:
            lines = text.strip().split("\n")
            records = []
            for line in lines[1:]:
                parts = line.split(",")
                if len(parts) >= 2:
                    try:
                        y = int(parts[0].strip())
                        t = parts[1].strip()
                        if t and t != "***":
                            records.append({"year": y, "temp_anomaly_c": float(t) / 100.0})
                    except Exception:
                        pass
            return pd.DataFrame(records).sort_values("year")

        def _synthetic_temp() -> pd.DataFrame:
            years = np.arange(1880, 2025)
            temp = -0.3 + 0.013 * (years - 1880) + 0.15 * np.sin(2 * np.pi * (years - 1880) / 11)
            temp += np.random.normal(0, 0.15, len(years))
            return pd.DataFrame({"year": years, "temp_anomaly_c": temp})

        return self.fetch(
            primary_url="https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv",
            backup_urls=["https://data.giss.nasa.gov/gistemp/tabledata_v3/GLB.Ts+dSST.csv"],
            parser=_parse_gistemp,
            cache_key="gistemp_global",
            synthetic_fallback=_synthetic_temp,
        )
