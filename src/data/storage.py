"""Data storage module"""

import sqlite3
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import pandas as pd
from decimal import Decimal

from ..utils.logger import logger


class DataStorage:
    """Data storage manager

    Uses SQLite to store historical market data
    """

    def __init__(self, db_path: str = "./data/db/trading.db"):
        """Initialize data storage

        Args:
            db_path: Database file path
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create OHLCV data table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ohlcv (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    symbol TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    UNIQUE(timestamp, symbol, exchange, timeframe)
                )
            """)

            # Create index
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_time
                ON ohlcv(symbol, exchange, timeframe, timestamp)
            """)

            # Create trades table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    commission REAL NOT NULL,
                    portfolio_value REAL NOT NULL,
                    strategy TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_session
                ON trades(session_id, timestamp)
            """)

            # Create equity curve table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS equity_curve (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    equity REAL NOT NULL,
                    cash REAL NOT NULL,
                    position_value REAL NOT NULL,
                    price REAL NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_equity_session
                ON equity_curve(session_id, timestamp)
            """)

            # Create backtest sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS backtest_sessions (
                    id TEXT PRIMARY KEY,
                    strategy TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    start_date DATETIME NOT NULL,
                    end_date DATETIME NOT NULL,
                    initial_capital REAL NOT NULL,
                    final_capital REAL NOT NULL,
                    total_return REAL NOT NULL,
                    total_trades INTEGER NOT NULL,
                    win_rate REAL,
                    sharpe_ratio REAL,
                    max_drawdown REAL,
                    config TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")

    def save_ohlcv(self, df: pd.DataFrame, symbol: str, exchange: str, timeframe: str):
        """Save OHLCV data

        Args:
            df: OHLCV data DataFrame
            symbol: Trading pair symbol
            exchange: Exchange
            timeframe: Time period
        """
        with sqlite3.connect(self.db_path) as conn:
            # Prepare data
            df = df.copy()
            df['symbol'] = symbol
            df['exchange'] = exchange
            df['timeframe'] = timeframe

            # Rename columns to match database
            if 'timestamp' not in df.columns and df.index.name == 'timestamp':
                df = df.reset_index()

            # Insert or replace data
            df.to_sql('ohlcv', conn, if_exists='append', index=False)
            logger.info(f"Saved {len(df)} records for {symbol} ({timeframe})")

    def load_ohlcv(
        self,
        symbol: str,
        exchange: str,
        timeframe: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Load OHLCV data

        Args:
            symbol: Trading pair symbol
            exchange: Exchange
            timeframe: Time period
            start: Start time
            end: End time

        Returns:
            OHLCV data DataFrame
        """
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT timestamp, open, high, low, close, volume
                FROM ohlcv
                WHERE symbol = ? AND exchange = ? AND timeframe = ?
            """
            params = [symbol, exchange, timeframe]

            if start:
                query += " AND timestamp >= ?"
                params.append(start.isoformat())

            if end:
                query += " AND timestamp <= ?"
                params.append(end.isoformat())

            query += " ORDER BY timestamp"

            df = pd.read_sql_query(query, conn, params=params, parse_dates=['timestamp'])

            if not df.empty:
                df.set_index('timestamp', inplace=True)

            logger.info(f"Loaded {len(df)} records for {symbol} ({timeframe})")
            return df

    def get_available_symbols(self, exchange: Optional[str] = None) -> List[str]:
        """Get list of available trading pairs

        Args:
            exchange: Exchange (optional)

        Returns:
            List of trading pairs
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if exchange:
                cursor.execute(
                    "SELECT DISTINCT symbol FROM ohlcv WHERE exchange = ?",
                    (exchange,)
                )
            else:
                cursor.execute("SELECT DISTINCT symbol FROM ohlcv")

            return [row[0] for row in cursor.fetchall()]

    def delete_data(
        self,
        symbol: Optional[str] = None,
        exchange: Optional[str] = None,
        before: Optional[datetime] = None
    ):
        """Delete data

        Args:
            symbol: Trading pair symbol (optional)
            exchange: Exchange (optional)
            before: Delete data before this time (optional)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            query = "DELETE FROM ohlcv WHERE 1=1"
            params = []

            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)

            if exchange:
                query += " AND exchange = ?"
                params.append(exchange)

            if before:
                query += " AND timestamp < ?"
                params.append(before.isoformat())

            cursor.execute(query, params)
            conn.commit()
            logger.info(f"Deleted {cursor.rowcount} records")

    def save_trades(self, trades: List[dict], session_id: str, strategy: str = ""):
        """Save trade records

        Args:
            trades: List of trade dictionaries
            session_id: Session ID
            strategy: Strategy name
        """
        if not trades:
            return

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            for trade in trades:
                cursor.execute("""
                    INSERT INTO trades (session_id, timestamp, symbol, side, quantity,
                                      price, commission, portfolio_value, strategy)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    trade['timestamp'].isoformat() if isinstance(trade['timestamp'], datetime) else trade['timestamp'],
                    trade['symbol'],
                    trade['side'],
                    trade['quantity'],
                    trade['price'],
                    trade['commission'],
                    trade['portfolio_value'],
                    strategy
                ))

            conn.commit()
            logger.info(f"Saved {len(trades)} trades for session {session_id}")

    def save_equity_curve(self, equity_data: List[dict], session_id: str):
        """Save equity curve data

        Args:
            equity_data: List of equity point dictionaries
            session_id: Session ID
        """
        if not equity_data:
            return

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            for point in equity_data:
                cursor.execute("""
                    INSERT INTO equity_curve (session_id, timestamp, equity, cash,
                                            position_value, price)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    point['timestamp'].isoformat() if isinstance(point['timestamp'], datetime) else point['timestamp'],
                    point['equity'],
                    point['cash'],
                    point['position_value'],
                    point['price']
                ))

            conn.commit()
            logger.info(f"Saved {len(equity_data)} equity points for session {session_id}")

    def save_backtest_session(self, session_data: dict):
        """Save backtest session metadata

        Args:
            session_data: Session metadata dictionary
        """
        import json

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO backtest_sessions
                (id, strategy, symbol, start_date, end_date, initial_capital,
                 final_capital, total_return, total_trades, win_rate,
                 sharpe_ratio, max_drawdown, config)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_data['id'],
                session_data['strategy'],
                session_data['symbol'],
                session_data['start_date'],
                session_data['end_date'],
                session_data['initial_capital'],
                session_data['final_capital'],
                session_data['total_return'],
                session_data['total_trades'],
                session_data.get('win_rate'),
                session_data.get('sharpe_ratio'),
                session_data.get('max_drawdown'),
                json.dumps(session_data.get('config', {}))
            ))

            conn.commit()
            logger.info(f"Saved backtest session {session_data['id']}")

    def load_trades(self, session_id: str) -> pd.DataFrame:
        """Load trade records

        Args:
            session_id: Session ID

        Returns:
            DataFrame of trades
        """
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT timestamp, symbol, side, quantity, price,
                       commission, portfolio_value, strategy
                FROM trades
                WHERE session_id = ?
                ORDER BY timestamp
            """
            df = pd.read_sql_query(query, conn, params=[session_id], parse_dates=['timestamp'])
            logger.info(f"Loaded {len(df)} trades for session {session_id}")
            return df

    def load_equity_curve(self, session_id: str) -> pd.DataFrame:
        """Load equity curve data

        Args:
            session_id: Session ID

        Returns:
            DataFrame of equity curve
        """
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT timestamp, equity, cash, position_value, price
                FROM equity_curve
                WHERE session_id = ?
                ORDER BY timestamp
            """
            df = pd.read_sql_query(query, conn, params=[session_id], parse_dates=['timestamp'])
            logger.info(f"Loaded {len(df)} equity points for session {session_id}")
            return df

    def get_backtest_sessions(self, limit: int = 10) -> pd.DataFrame:
        """Get recent backtest sessions

        Args:
            limit: Maximum number of sessions to return

        Returns:
            DataFrame of sessions
        """
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT id, strategy, symbol, start_date, end_date,
                       initial_capital, final_capital, total_return,
                       total_trades, win_rate, sharpe_ratio, max_drawdown,
                       created_at
                FROM backtest_sessions
                ORDER BY created_at DESC
                LIMIT ?
            """
            df = pd.read_sql_query(query, conn, params=[limit], parse_dates=['start_date', 'end_date', 'created_at'])
            return df

    def export_trades_csv(self, session_id: str, output_path: str):
        """Export trades to CSV

        Args:
            session_id: Session ID
            output_path: Output file path
        """
        df = self.load_trades(session_id)
        df.to_csv(output_path, index=False)
        logger.info(f"Exported trades to {output_path}")

    def export_equity_csv(self, session_id: str, output_path: str):
        """Export equity curve to CSV

        Args:
            session_id: Session ID
            output_path: Output file path
        """
        df = self.load_equity_curve(session_id)
        df.to_csv(output_path, index=False)
        logger.info(f"Exported equity curve to {output_path}")
