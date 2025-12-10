"""Data logging module for trade and BBO data."""
import csv
import json
import os
import logging
from decimal import Decimal
from datetime import datetime
import pytz


class DataLogger:
    """Handles CSV and JSON logging for trades and BBO data."""

    def __init__(self, exchange: str, ticker: str, logger: logging.Logger):
        """Initialize data logger with file paths."""
        self.exchange = exchange
        self.ticker = ticker
        self.logger = logger
        os.makedirs("logs", exist_ok=True)

        self.csv_filename = f"logs/{exchange}_{ticker}_trades.csv"
        self.bbo_csv_filename = f"logs/{exchange}_{ticker}_bbo_data.csv"
        self.spread_stats_csv_filename = f"logs/{exchange}_{ticker}_spread_stats.csv"
        self.thresholds_json_filename = f"logs/{exchange}_{ticker}_thresholds.json"

        # CSV file handles for efficient writing (kept open)
        self.bbo_csv_file = None
        self.bbo_csv_writer = None
        self.bbo_write_counter = 0
        self.bbo_flush_interval = 10  # Flush every N writes
        
        # Spread stats CSV file handles
        self.spread_stats_csv_file = None
        self.spread_stats_csv_writer = None
        self.spread_stats_write_counter = 0
        self.spread_stats_flush_interval = 10  # Flush every N writes

        self._initialize_csv_file()
        self._initialize_bbo_csv_file()
        self._initialize_spread_stats_csv_file()

    def _initialize_csv_file(self):
        """Initialize CSV file with headers if it doesn't exist."""
        if not os.path.exists(self.csv_filename):
            with open(self.csv_filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['exchange', 'timestamp', 'side', 'price', 'quantity'])

    def _initialize_bbo_csv_file(self):
        """Initialize BBO CSV file with headers if it doesn't exist."""
        file_exists = os.path.exists(self.bbo_csv_filename)

        # Open file in append mode (will create if doesn't exist)
        self.bbo_csv_file = open(self.bbo_csv_filename, 'a', newline='', buffering=8192)  # 8KB buffer
        self.bbo_csv_writer = csv.writer(self.bbo_csv_file)

        # Write header only if file is new
        if not file_exists:
            self.bbo_csv_writer.writerow([
                'timestamp',
                'maker_bid',
                'maker_ask',
                'taker_bid',
                'taker_ask',
                'long_maker_spread',
                'short_maker_spread',
                'long_maker',
                'short_maker',
                'long_maker_threshold',
                'short_maker_threshold'
            ])
            self.bbo_csv_file.flush()  # Ensure header is written immediately

    def _initialize_spread_stats_csv_file(self):
        """Initialize spread statistics CSV file with headers if it doesn't exist."""
        file_exists = os.path.exists(self.spread_stats_csv_filename)

        # Open file in append mode (will create if doesn't exist)
        self.spread_stats_csv_file = open(self.spread_stats_csv_filename, 'a', newline='', buffering=8192)
        self.spread_stats_csv_writer = csv.writer(self.spread_stats_csv_file)

        # Write header only if file is new
        if not file_exists:
            self.spread_stats_csv_writer.writerow([
                'timestamp',
                'spread',
                'spread_type',
                'moving_average',
                'rolling_std',
                'count',
                'min',
                'max'
            ])
            self.spread_stats_csv_file.flush()  # Ensure header is written immediately

    def log_trade_to_csv(self, exchange: str, side: str, price: str, quantity: str):
        """Log trade details to CSV file."""
        timestamp = datetime.now(pytz.UTC).isoformat()

        with open(self.csv_filename, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                exchange,
                timestamp,
                side,
                price,
                quantity
            ])

        self.logger.info(f"📊 Trade logged to CSV: {exchange} {side} {quantity} @ {price}")

    def log_bbo_to_csv(self, maker_bid: Decimal, maker_ask: Decimal, taker_bid: Decimal,
                       taker_ask: Decimal, long_maker: bool, short_maker: bool,
                       long_maker_threshold: Decimal, short_maker_threshold: Decimal):
        """Log BBO data to CSV file using buffered writes."""
        if not self.bbo_csv_file or not self.bbo_csv_writer:
            # Fallback: reinitialize if file handle is lost
            self._initialize_bbo_csv_file()

        timestamp = datetime.now(pytz.UTC).isoformat()

        # Calculate spreads
        long_maker_spread = (taker_bid - maker_bid
                             if taker_bid and taker_bid > 0 and maker_bid > 0
                             else Decimal('0'))
        short_maker_spread = (maker_ask - taker_ask
                              if maker_ask > 0 and taker_ask and taker_ask > 0
                              else Decimal('0'))

        try:
            self.bbo_csv_writer.writerow([
                timestamp,
                str(maker_bid),
                str(maker_ask),
                str(taker_bid),
                str(taker_ask),
                str(long_maker_spread),
                str(short_maker_spread),
                long_maker,
                short_maker,
                str(long_maker_threshold),
                str(short_maker_threshold)
            ])

            # Increment write counter and flush periodically
            self.bbo_write_counter += 1
            if self.bbo_write_counter >= self.bbo_flush_interval:
                self.bbo_csv_file.flush()
                self.bbo_write_counter = 0

        except Exception as e:
            self.logger.error(f"❌ Error writing BBO data to CSV: {e}")

    def log_spread_stats_to_csv(self, spread: float, spread_type: str, 
                                moving_average: float, rolling_std: float,
                                count: int, min_spread: float, max_spread: float):
        """Log spread statistics to CSV file using buffered writes.
        
        Args:
            spread: Current spread value
            spread_type: 'long' or 'short'
            moving_average: Moving average of spread
            rolling_std: Rolling standard deviation
            count: Number of spreads in calculation
            min_spread: Minimum spread in window
            max_spread: Maximum spread in window
        """
        if not self.spread_stats_csv_file or not self.spread_stats_csv_writer:
            # Fallback: reinitialize if file handle is lost
            self._initialize_spread_stats_csv_file()

        timestamp = datetime.now(pytz.UTC).isoformat()

        try:
            self.spread_stats_csv_writer.writerow([
                timestamp,
                f"{spread:.2f}",
                spread_type,
                f"{moving_average:.2f}",
                f"{rolling_std:.2f}",
                count,
                f"{min_spread:.2f}",
                f"{max_spread:.2f}"
            ])

            # Increment write counter and flush periodically
            self.spread_stats_write_counter += 1
            if self.spread_stats_write_counter >= self.spread_stats_flush_interval:
                self.spread_stats_csv_file.flush()
                self.spread_stats_write_counter = 0

        except Exception as e:
            self.logger.error(f"❌ Error writing spread stats to CSV: {e}")

    def close(self):
        """Close CSV file handles."""
        if self.bbo_csv_file:
            try:
                self.bbo_csv_file.flush()
                self.bbo_csv_file.close()
            except Exception as e:
                self.logger.error(f"Error closing BBO CSV file: {e}")
        
        if self.spread_stats_csv_file:
            try:
                self.spread_stats_csv_file.flush()
                self.spread_stats_csv_file.close()
            except Exception as e:
                self.logger.error(f"Error closing spread stats CSV file: {e}")
