#!/usr/bin/env python3
"""
Sentiment Cache Cleanup Script
Automatically removes old sentiment data to prevent memory buildup
"""

import argparse
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path


# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def cleanup_sentiment_cache(cache_file: str, max_age_hours: int = 24, dry_run: bool = False):
    """
    Clean up old sentiment cache data

    Args:
        cache_file: Path to sentiment cache file
        max_age_hours: Maximum age of data to keep (in hours)
        dry_run: If True, only show what would be deleted
    """
    cache_path = Path(cache_file)

    if not cache_path.exists():
        logger.warning(f"Cache file {cache_file} does not exist")
        return

    try:
        # Load current cache
        with open(cache_path) as f:
            cache_data = json.load(f)

        if "fear_greed" not in cache_data or "values" not in cache_data["fear_greed"]:
            logger.warning("Invalid cache format")
            return

        values = cache_data["fear_greed"]["values"]
        original_count = len(values)

        # Calculate cutoff time
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        # Find old entries
        old_entries = []
        for timestamp_str, value in values.items():
            try:
                entry_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                if entry_time < cutoff_time:
                    old_entries.append(timestamp_str)
            except ValueError:
                logger.warning(f"Invalid timestamp format: {timestamp_str}")
                continue

        if not old_entries:
            logger.info("No old entries found to clean up")
            return

        logger.info(f"Found {len(old_entries)} old entries to remove")
        logger.info(f"Oldest entry: {min(old_entries)}")
        logger.info(f"Cutoff time: {cutoff_time.isoformat()}")

        if dry_run:
            logger.info("DRY RUN: Would remove the following entries:")
            for entry in old_entries[:10]:  # Show first 10
                logger.info(f"  {entry}: {values[entry]}")
            if len(old_entries) > 10:
                logger.info(f"  ... and {len(old_entries) - 10} more")
            return

        # Remove old entries
        for entry in old_entries:
            del values[entry]

        # Update last timestamp
        if values:
            latest_timestamp = max(values.keys())
            cache_data["fear_greed"]["last"] = datetime.fromisoformat(
                latest_timestamp.replace("Z", "+00:00")
            ).timestamp()

        # Save cleaned cache
        with open(cache_path, "w") as f:
            json.dump(cache_data, f, indent=2)

        logger.info(f"Successfully removed {len(old_entries)} old entries")
        logger.info(f"Cache reduced from {original_count} to {len(values)} entries")

    except Exception as e:
        logger.error(f"Error cleaning up cache: {e}")


def main():
    parser = argparse.ArgumentParser(description="Clean up old sentiment cache data")
    parser.add_argument(
        "--cache-file",
        default="user_data/sentiment_cache.json",
        help="Path to sentiment cache file",
    )
    parser.add_argument(
        "--max-age-hours", type=int, default=24, help="Maximum age of data to keep (in hours)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )

    args = parser.parse_args()

    logger.info("Starting sentiment cache cleanup")
    logger.info(f"Cache file: {args.cache_file}")
    logger.info(f"Max age: {args.max_age_hours} hours")
    logger.info(f"Dry run: {args.dry_run}")

    cleanup_sentiment_cache(
        cache_file=args.cache_file, max_age_hours=args.max_age_hours, dry_run=args.dry_run
    )

    logger.info("Sentiment cache cleanup completed")


if __name__ == "__main__":
    main()
