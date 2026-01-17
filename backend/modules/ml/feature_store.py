"""
Feature Store for Adaptive Intelligence Engine
Centralizes feature computation and storage for ML training
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from utils.logger import setup_logger
from utils.binance_client import binance_client
from api.models.database import SessionLocal
from api.models.ml_models import MLTradeFeature

logger = setup_logger("feature_store")


class FeatureStore:
    """
    Centralizes features of market data, indicators, and trade metadata
    """

    MARKET_FEATURES = [
        # Volatility
        'atr_1m', 'atr_5m', 'atr_1h',
        'bb_width_1m', 'bb_width_5m',

        # Trend
        'adx_1m', 'adx_5m', 'adx_1h',
        'ema_slope_fast', 'ema_slope_slow',

        # Momentum
        'rsi_1m', 'rsi_5m', 'rsi_1h',
        'macd_histogram', 'macd_signal_cross',
        'rsi_divergence_bull', 'rsi_divergence_bear',

        # Volume
        'volume_ratio', 'volume_trend',
        'vwap_distance', 'vwap_slope',

        # Market Regime
        'btc_correlation_15m',
        'market_hour', 'day_of_week',
        'us_market_session', 'asian_session',

        # Spread
        'spread_bps',
    ]

    def __init__(self):
        self.db: Optional[Session] = None

    async def compute_features(
        self,
        symbol: str,
        timestamp: Optional[datetime] = None
    ) -> Dict:
        """
        Compute all features for a symbol at a given timestamp

        Args:
            symbol: Trading pair symbol
            timestamp: Time of feature computation (defaults to now)

        Returns:
            Dictionary of computed features
        """
        if timestamp is None:
            timestamp = datetime.now()

        logger.debug(f"Computing features for {symbol} at {timestamp}")

        try:
            # Fetch multi-timeframe data
            klines_1m = await binance_client.get_historical_klines(
                symbol, "1m", limit=100
            )
            klines_5m = await binance_client.get_historical_klines(
                symbol, "5m", limit=100
            )
            klines_1h = await binance_client.get_historical_klines(
                symbol, "1h", limit=50
            )

            # Convert to DataFrames
            df_1m = self._klines_to_df(klines_1m)
            df_5m = self._klines_to_df(klines_5m)
            df_1h = self._klines_to_df(klines_1h)

            # Compute features
            features = {}

            # Volatility features
            features.update(self._compute_volatility_features(df_1m, df_5m, df_1h))

            # Trend features
            features.update(self._compute_trend_features(df_1m, df_5m, df_1h))

            # Momentum features
            features.update(self._compute_momentum_features(df_1m, df_5m, df_1h))

            # Volume features
            features.update(self._compute_volume_features(df_1m))

            # Market context features
            features.update(self._compute_market_context_features(timestamp, symbol))

            # Spread features
            features.update(await self._compute_spread_features(symbol))

            features['symbol'] = symbol
            features['timestamp'] = timestamp

            return features

        except Exception as e:
            logger.error(f"Error computing features for {symbol}: {e}")
            return {}

    def _klines_to_df(self, klines: List) -> pd.DataFrame:
        """Convert klines to DataFrame with technical indicators"""
        if not klines:
            return pd.DataFrame()

        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])

        # Convert to numeric
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])

        return df

    def _compute_volatility_features(
        self,
        df_1m: pd.DataFrame,
        df_5m: pd.DataFrame,
        df_1h: pd.DataFrame
    ) -> Dict:
        """Compute volatility-based features"""
        features = {}

        # ATR (Average True Range)
        features['atr_1m'] = self._calculate_atr(df_1m, period=14)
        features['atr_5m'] = self._calculate_atr(df_5m, period=14)
        features['atr_1h'] = self._calculate_atr(df_1h, period=14)

        # Bollinger Bands Width
        features['bb_width_1m'] = self._calculate_bb_width(df_1m, period=20)
        features['bb_width_5m'] = self._calculate_bb_width(df_5m, period=20)

        return features

    def _compute_trend_features(
        self,
        df_1m: pd.DataFrame,
        df_5m: pd.DataFrame,
        df_1h: pd.DataFrame
    ) -> Dict:
        """Compute trend-based features"""
        features = {}

        # ADX (Average Directional Index)
        features['adx_1m'] = self._calculate_adx(df_1m, period=14)
        features['adx_5m'] = self._calculate_adx(df_5m, period=14)
        features['adx_1h'] = self._calculate_adx(df_1h, period=14)

        # EMA Slopes
        ema_fast_1m = df_1m['close'].ewm(span=12, adjust=False).mean()
        ema_slow_1m = df_1m['close'].ewm(span=26, adjust=False).mean()

        features['ema_slope_fast'] = float((ema_fast_1m.iloc[-1] - ema_fast_1m.iloc[-2]) / ema_fast_1m.iloc[-2])
        features['ema_slope_slow'] = float((ema_slow_1m.iloc[-1] - ema_slow_1m.iloc[-2]) / ema_slow_1m.iloc[-2])

        return features

    def _compute_momentum_features(
        self,
        df_1m: pd.DataFrame,
        df_5m: pd.DataFrame,
        df_1h: pd.DataFrame
    ) -> Dict:
        """Compute momentum-based features"""
        features = {}

        # RSI
        features['rsi_1m'] = self._calculate_rsi(df_1m, period=14)
        features['rsi_5m'] = self._calculate_rsi(df_5m, period=14)
        features['rsi_1h'] = self._calculate_rsi(df_1h, period=14)

        # MACD
        macd_hist = self._calculate_macd_histogram(df_1m)
        features['macd_histogram'] = macd_hist
        features['macd_signal_cross'] = self._detect_macd_cross(df_1m)

        # RSI Divergence
        div_bull, div_bear = self._detect_rsi_divergence(df_1m)
        features['rsi_divergence_bull'] = div_bull
        features['rsi_divergence_bear'] = div_bear

        return features

    def _compute_volume_features(self, df_1m: pd.DataFrame) -> Dict:
        """Compute volume-based features"""
        features = {}

        # Volume Ratio
        vol_avg = df_1m['volume'].rolling(window=20).mean().iloc[-1]
        vol_current = df_1m['volume'].iloc[-1]
        features['volume_ratio'] = float(vol_current / vol_avg) if vol_avg > 0 else 1.0

        # Volume Trend
        vol_slope = (df_1m['volume'].iloc[-1] - df_1m['volume'].iloc[-5]) / 5
        features['volume_trend'] = float(vol_slope)

        # VWAP Distance
        vwap = (df_1m['close'] * df_1m['volume']).sum() / df_1m['volume'].sum()
        current_price = df_1m['close'].iloc[-1]
        features['vwap_distance'] = float((current_price - vwap) / vwap)

        # VWAP Slope
        vwap_prev = (df_1m['close'].iloc[:-1] * df_1m['volume'].iloc[:-1]).sum() / df_1m['volume'].iloc[:-1].sum()
        features['vwap_slope'] = float((vwap - vwap_prev) / vwap_prev) if vwap_prev > 0 else 0.0

        return features

    def _compute_market_context_features(self, timestamp: datetime, symbol: str) -> Dict:
        """Compute market context features (time, session, correlation)"""
        features = {}

        # Time features
        features['market_hour'] = timestamp.hour
        features['day_of_week'] = timestamp.weekday()

        # Trading sessions
        hour = timestamp.hour
        features['us_market_session'] = 13 <= hour <= 20  # NYC 9am - 4pm EST
        features['asian_session'] = 0 <= hour <= 8  # Tokyo/HK morning

        # BTC correlation (placeholder - requires historical data)
        # For now, default to neutral
        features['btc_correlation_15m'] = 0.5

        return features

    async def _compute_spread_features(self, symbol: str) -> Dict:
        """Compute spread-based features"""
        features = {}

        try:
            ticker = await binance_client.get_ticker(symbol)
            bid = float(ticker.get('bidPrice', 0))
            ask = float(ticker.get('askPrice', 0))

            if bid > 0 and ask > 0:
                spread = (ask - bid) / bid
                features['spread_bps'] = spread * 10000  # Convert to basis points
            else:
                features['spread_bps'] = 0.0

        except Exception as e:
            logger.warning(f"Error computing spread for {symbol}: {e}")
            features['spread_bps'] = 0.0

        return features

    # Technical indicator calculations
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range"""
        if len(df) < period:
            return 0.0

        high = df['high']
        low = df['low']
        close = df['close']

        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean().iloc[-1]

        return float(atr) if not pd.isna(atr) else 0.0

    def _calculate_bb_width(self, df: pd.DataFrame, period: int = 20) -> float:
        """Calculate Bollinger Bands Width"""
        if len(df) < period:
            return 0.0

        sma = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()

        bb_width = (std.iloc[-1] * 2) / sma.iloc[-1] if sma.iloc[-1] > 0 else 0.0

        return float(bb_width) if not pd.isna(bb_width) else 0.0

    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average Directional Index"""
        if len(df) < period + 1:
            return 0.0

        high = df['high']
        low = df['low']
        close = df['close']

        # Calculate +DM and -DM
        high_diff = high.diff()
        low_diff = -low.diff()

        plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
        minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)

        # Calculate TR
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Smooth +DM, -DM, TR
        atr = tr.rolling(window=period).mean()
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

        # Calculate DX and ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean().iloc[-1]

        return float(adx) if not pd.isna(adx) else 0.0

    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        if len(df) < period + 1:
            return 50.0

        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0

    def _calculate_macd_histogram(self, df: pd.DataFrame) -> float:
        """Calculate MACD Histogram"""
        if len(df) < 26:
            return 0.0

        ema_fast = df['close'].ewm(span=12, adjust=False).mean()
        ema_slow = df['close'].ewm(span=26, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line

        return float(histogram.iloc[-1]) if not pd.isna(histogram.iloc[-1]) else 0.0

    def _detect_macd_cross(self, df: pd.DataFrame) -> bool:
        """Detect MACD signal line crossover"""
        if len(df) < 27:
            return False

        ema_fast = df['close'].ewm(span=12, adjust=False).mean()
        ema_slow = df['close'].ewm(span=26, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=9, adjust=False).mean()

        # Bullish cross: MACD crosses above signal
        cross = (macd_line.iloc[-2] <= signal_line.iloc[-2]) and (macd_line.iloc[-1] > signal_line.iloc[-1])

        return bool(cross)

    def _detect_rsi_divergence(self, df: pd.DataFrame) -> Tuple[bool, bool]:
        """Detect RSI divergence (bullish and bearish)"""
        if len(df) < 30:
            return False, False

        rsi = df['close'].diff().rolling(window=14).apply(
            lambda x: 100 - (100 / (1 + (x[x > 0].mean() / -x[x < 0].mean())))
        )

        # Simple divergence detection (can be enhanced)
        price_trend_up = df['close'].iloc[-1] > df['close'].iloc[-10]
        rsi_trend_down = rsi.iloc[-1] < rsi.iloc[-10]

        bullish_div = price_trend_up and rsi_trend_down

        price_trend_down = df['close'].iloc[-1] < df['close'].iloc[-10]
        rsi_trend_up = rsi.iloc[-1] > rsi.iloc[-10]

        bearish_div = price_trend_down and rsi_trend_up

        return bullish_div, bearish_div

    async def store_trade_outcome(
        self,
        trade_id: str,
        features: Dict,
        outcome: Dict
    ):
        """
        Store features and trade outcome for ML training

        Args:
            trade_id: Trade identifier
            features: Dictionary of computed features
            outcome: Dictionary with 'outcome' ('WIN'/'LOSS'), 'pnl_pct', etc.
        """
        try:
            with SessionLocal() as db:
                ml_feature = MLTradeFeature(
                    trade_id=trade_id,
                    timestamp=features.get('timestamp', datetime.now()),
                    symbol=features.get('symbol', ''),

                    # Volatility
                    atr_1m=features.get('atr_1m'),
                    atr_5m=features.get('atr_5m'),
                    atr_1h=features.get('atr_1h'),
                    bb_width_1m=features.get('bb_width_1m'),
                    bb_width_5m=features.get('bb_width_5m'),

                    # Trend
                    adx_1m=features.get('adx_1m'),
                    adx_5m=features.get('adx_5m'),
                    adx_1h=features.get('adx_1h'),
                    ema_slope_fast=features.get('ema_slope_fast'),
                    ema_slope_slow=features.get('ema_slope_slow'),

                    # Momentum
                    rsi_1m=features.get('rsi_1m'),
                    rsi_5m=features.get('rsi_5m'),
                    rsi_1h=features.get('rsi_1h'),
                    macd_histogram=features.get('macd_histogram'),
                    macd_signal_cross=features.get('macd_signal_cross'),
                    rsi_divergence_bull=features.get('rsi_divergence_bull'),
                    rsi_divergence_bear=features.get('rsi_divergence_bear'),

                    # Volume
                    volume_ratio=features.get('volume_ratio'),
                    volume_trend=features.get('volume_trend'),
                    vwap_distance=features.get('vwap_distance'),
                    vwap_slope=features.get('vwap_slope'),

                    # Market context
                    btc_correlation_15m=features.get('btc_correlation_15m'),
                    market_hour=features.get('market_hour'),
                    day_of_week=features.get('day_of_week'),
                    us_market_session=features.get('us_market_session'),
                    asian_session=features.get('asian_session'),

                    # Spread
                    spread_bps=features.get('spread_bps'),

                    # Regime (will be set later)
                    market_regime=features.get('market_regime'),

                    # Outcome
                    outcome=outcome.get('outcome'),
                    pnl_pct=outcome.get('pnl_pct'),
                    pnl_absolute=outcome.get('pnl_absolute'),
                    duration_minutes=outcome.get('duration_minutes')
                )

                db.add(ml_feature)
                db.commit()

                logger.info(f"✅ Stored ML features for trade {trade_id}")

        except Exception as e:
            logger.error(f"Error storing trade outcome: {e}")

    async def get_trade_features(self, trade_id: str) -> Optional[Dict]:
        """Retrieve stored features for a trade"""
        try:
            with SessionLocal() as db:
                result = db.execute(
                    select(MLTradeFeature).where(MLTradeFeature.trade_id == trade_id)
                ).scalar_one_or_none()

                if result:
                    return {col: getattr(result, col) for col in self.MARKET_FEATURES}
                return None

        except Exception as e:
            logger.error(f"Error retrieving trade features: {e}")
            return None

    async def get_historical_features(
        self,
        days: int = 30,
        regime: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Retrieve historical features for training

        Args:
            days: Number of days to look back
            regime: Optional filter by market regime

        Returns:
            DataFrame with historical features and outcomes
        """
        try:
            with SessionLocal() as db:
                cutoff = datetime.now() - timedelta(days=days)

                query = select(MLTradeFeature).where(
                    MLTradeFeature.timestamp >= cutoff
                )

                if regime is not None:
                    query = query.where(MLTradeFeature.market_regime == regime)

                results = db.execute(query).scalars().all()

                if not results:
                    return pd.DataFrame()

                # Convert to DataFrame
                data = []
                for r in results:
                    row = {col: getattr(r, col) for col in self.MARKET_FEATURES}
                    row['outcome'] = r.outcome
                    row['pnl_pct'] = r.pnl_pct
                    row['symbol'] = r.symbol
                    data.append(row)

                return pd.DataFrame(data)

        except Exception as e:
            logger.error(f"Error retrieving historical features: {e}")
            return pd.DataFrame()


# Singleton instance
feature_store = FeatureStore()
