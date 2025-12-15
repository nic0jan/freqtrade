"""
Background Trade Data Fetcher
Handles asynchronous trade data fetching to prevent blocking the main bot loop
"""

import asyncio
import logging
import time
from collections import deque
from typing import Any

from pandas import DataFrame

from freqtrade.constants import Config, ListPairsWithTimeframes, PairWithTimeframe
from freqtrade.exchange import Exchange


logger = logging.getLogger(__name__)


class BackgroundTradeFetcher:
    """
    Background thread for fetching trade data without blocking the main bot loop
    """

    def __init__(self, exchange: Exchange, config: Config):
        self._exchange = exchange
        self._config = config
        self._task: asyncio.Task | None = None
        self._data_queue: deque = deque()
        self._last_fetch_time: dict[PairWithTimeframe, float] = {}
        self._fetch_interval = config.get("internals", {}).get(
            "trade_data_fetch_interval", 30
        )  # seconds
        self._max_queue_size = config.get("internals", {}).get("trade_data_queue_size", 100)

        # Background processing settings
        self._background_enabled = self._config.get("exchange", {}).get(
            "use_public_trades", False
        )

    def start(self) -> None:
        """Start the background trade fetching task"""
        if not self._background_enabled:
            logger.info("Background trade fetching is disabled")
            return

        if self._task and not self._task.done():
            logger.warning("Background trade fetcher is already running")
            return

        self._task = asyncio.create_task(self._run_background_loop())
        logger.info("Background trade fetcher started")

    def stop(self) -> None:
        """Stop the background trade fetching task"""
        if self._task and not self._task.done():
            self._task.cancel()
            logger.info("Background trade fetcher stopped")

    async def _run_background_loop(self) -> None:
        """Main background loop for fetching trade data"""
        while True:
            try:
                # Get pairs that need trade data refresh
                pairs_to_fetch = self._get_pairs_needing_refresh()

                if pairs_to_fetch:
                    logger.debug(
                        f"Background fetching trade data for {len(pairs_to_fetch)} pairs"
                    )

                    # Fetch trade data asynchronously
                    await self._fetch_trades_background(pairs_to_fetch)

                # Wait before next iteration
                await asyncio.sleep(self._fetch_interval)

            except asyncio.CancelledError:
                logger.info("Background trade fetcher cancelled")
                break
            except Exception as e:
                logger.error(f"Error in background trade fetcher: {e}")
                await asyncio.sleep(5)  # Wait 5 seconds before retrying

    def _get_pairs_needing_refresh(self) -> ListPairsWithTimeframes:
        """Get pairs that need trade data refresh based on timing and configuration"""
        current_time = time.time()
        pairs_to_fetch = []

        # Get active pairs from exchange
        if hasattr(self._exchange, "_klines"):
            active_pairs = list(self._exchange._klines.keys())
        else:
            active_pairs = []

        for pair in active_pairs:
            last_fetch = self._last_fetch_time.get(pair, 0)

            # Check if enough time has passed since last fetch
            if current_time - last_fetch >= self._fetch_interval:
                pairs_to_fetch.append(pair)

        return pairs_to_fetch

    async def _fetch_trades_background(self, pairs: ListPairsWithTimeframes) -> None:
        """Fetch trade data for pairs in background"""
        if not pairs:
            return

        try:
            # Use the exchange's existing async trade fetching
            results = await self._exchange._async_refresh_trades(pairs)

            # Process results and update exchange cache
            for pair, trades_df in results.items():
                if trades_df is not None:
                    # Update exchange's internal trade cache
                    self._exchange._trades[pair] = trades_df
                    self._last_fetch_time[pair] = time.time()

                    logger.debug(f"Background updated trade data for {pair}")

        except Exception as e:
            logger.error(f"Error fetching trades in background: {e}")

    def get_latest_trades(self, pair: PairWithTimeframe) -> DataFrame | None:
        """Get the latest trade data for a pair (non-blocking)"""
        return self._exchange._trades.get(pair)

    def is_data_fresh(self, pair: PairWithTimeframe) -> bool:
        """Check if trade data for a pair is fresh enough"""
        current_time = time.time()
        last_fetch = self._last_fetch_time.get(pair, 0)
        return current_time - last_fetch < self._fetch_interval

    def get_stats(self) -> dict[str, Any]:
        """Get background fetcher statistics"""
        return {
            "is_running": self._task is not None and not self._task.done(),
            "queue_size": len(self._data_queue),
            "pairs_tracked": len(self._last_fetch_time),
            "fetch_interval": self._fetch_interval,
            "background_enabled": self._background_enabled,
        }

