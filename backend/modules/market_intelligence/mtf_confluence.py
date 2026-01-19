"""
Multi-Timeframe Confluence Analyzer
Analyzes multiple timeframes to identify high-probability setups with trend alignment
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np

from utils.logger import setup_logger
from utils.binance_client import binance_client

logger = setup_logger("mtf_confluence")


class TimeframeSignal:
    """Represents a signal from a single timeframe"""

    def __init__(
        self,
        timeframe: str,
        direction: str,
        strength: int,
        indicators: Dict
    ):
        self.timeframe = timeframe
        self.direction = direction  # 'BULLISH', 'BEARISH', 'NEUTRAL'
        self.strength = strength  # 0-100
        self.indicators = indicators
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict:
        return {
            'timeframe': self.timeframe,
            'direction': self.direction,
            'strength': self.strength,
            'indicators': self.indicators,
            'timestamp': self.timestamp.isoformat()
        }


class MultiTimeframeConfluence:
    """
    Analyzes multiple timeframes to calculate confluence score

    Higher timeframes (1h, 4h, 1d) carry more weight
    Perfect alignment across all timeframes = 100 score
    """

    def __init__(self):
        self.cache = {}
        self.cache_ttl = 30  # 30 seconds

        # Timeframes to analyze (in order of importance)
        self.timeframes = {
            '1m': {'interval': '1m', 'weight': 0.05, 'lookback': 100},
            '5m': {'interval': '5m', 'weight': 0.10, 'lookback': 100},
            '15m': {'interval': '15m', 'weight': 0.15, 'lookback': 100},
            '1h': {'interval': '1h', 'weight': 0.25, 'lookback': 100},
            '4h': {'interval': '4h', 'weight': 0.25, 'lookback': 100},
            '1d': {'interval': '1d', 'weight': 0.20, 'lookback': 50},
        }

    async def analyze_confluence(self, symbol: str) -> Dict:
        """
        Analyze multi-timeframe confluence

        Returns:
            Confluence analysis with score and signals per timeframe
        """
        cache_key = f"{symbol}_mtf_confluence"

        # Check cache
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if (datetime.now() - cached['timestamp']).seconds < self.cache_ttl:
                return cached

        try:
            # Analyze each timeframe in parallel
            tasks = []
            for tf_name, tf_config in self.timeframes.items():
                task = self._analyze_timeframe(symbol, tf_name, tf_config)
                tasks.append(task)

            timeframe_signals = await asyncio.gather(*tasks)

            # Filter out failed analyses
            valid_signals = [s for s in timeframe_signals if s is not None]

            if not valid_signals:
                return {}

            # Calculate weighted confluence score
            confluence_score = self._calculate_confluence_score(valid_signals)

            # Determine overall direction
            overall_direction = self._determine_overall_direction(valid_signals)

            # Generate trading signals
            signals = self._generate_signals(
                valid_signals,
                confluence_score,
                overall_direction
            )

            result = {
                'symbol': symbol,
                'timestamp': datetime.now(),

                # Confluence metrics
                'confluence_score': confluence_score,
                'overall_direction': overall_direction,
                'aligned_timeframes': len([s for s in valid_signals if s.direction == overall_direction]),
                'total_timeframes': len(valid_signals),

                # Individual timeframe signals
                'timeframe_signals': [s.to_dict() for s in valid_signals],

                # Trading signals
                **signals
            }

            # Cache
            self.cache[cache_key] = result

            return result

        except Exception as e:
            logger.error(f"Error analyzing confluence for {symbol}: {e}")
            return {}

    async def _analyze_timeframe(
        self,
        symbol: str,
        tf_name: str,
        tf_config: Dict
    ) -> Optional[TimeframeSignal]:
        """
        Analyze a single timeframe

        Returns:
            TimeframeSignal object or None if analysis failed
        """
        try:
            interval = tf_config['interval']
            lookback = tf_config['lookback']

            # Get candles
            klines = await binance_client.futures_klines(
                symbol=symbol,
                interval=interval,
                limit=lookback
            )

            if not klines or len(klines) < 50:
                return None

            # Extract OHLCV
            closes = np.array([float(k[4]) for k in klines])
            highs = np.array([float(k[2]) for k in klines])
            lows = np.array([float(k[3]) for k in klines])
            volumes = np.array([float(k[5]) for k in klines])

            # Calculate indicators
            indicators = self._calculate_indicators(closes, highs, lows, volumes)

            # Determine direction and strength
            direction, strength = self._evaluate_timeframe(indicators, closes)

            signal = TimeframeSignal(
                timeframe=tf_name,
                direction=direction,
                strength=strength,
                indicators=indicators
            )

            return signal

        except Exception as e:
            logger.error(f"Error analyzing {tf_name} for {symbol}: {e}")
            return None

    def _calculate_indicators(
        self,
        closes: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        volumes: np.ndarray
    ) -> Dict:
        """
        Calculate technical indicators for confluence analysis

        Returns:
            Dict with indicator values
        """
        indicators = {}

        # EMAs
        ema_20 = self._ema(closes, 20)
        ema_50 = self._ema(closes, 50)
        ema_200 = self._ema(closes, 200) if len(closes) >= 200 else ema_50

        indicators['ema_20'] = ema_20[-1]
        indicators['ema_50'] = ema_50[-1]
        indicators['ema_200'] = ema_200[-1]

        current_price = closes[-1]

        # EMA alignment
        indicators['above_ema_20'] = current_price > ema_20[-1]
        indicators['above_ema_50'] = current_price > ema_50[-1]
        indicators['above_ema_200'] = current_price > ema_200[-1]

        # EMA trend
        indicators['ema_20_rising'] = ema_20[-1] > ema_20[-5]
        indicators['ema_50_rising'] = ema_50[-1] > ema_50[-5]

        # RSI
        rsi = self._rsi(closes, 14)
        indicators['rsi'] = rsi[-1]
        indicators['rsi_oversold'] = rsi[-1] < 30
        indicators['rsi_overbought'] = rsi[-1] > 70

        # MACD
        macd_line, signal_line = self._macd(closes)
        indicators['macd'] = macd_line[-1]
        indicators['macd_signal'] = signal_line[-1]
        indicators['macd_bullish'] = macd_line[-1] > signal_line[-1]

        # ADX (trend strength)
        adx = self._adx(highs, lows, closes, 14)
        indicators['adx'] = adx[-1]
        indicators['strong_trend'] = adx[-1] > 25

        # ATR (volatility)
        atr = self._atr(highs, lows, closes, 14)
        indicators['atr'] = atr[-1]
        indicators['atr_pct'] = (atr[-1] / current_price) * 100

        # Volume trend
        avg_volume = np.mean(volumes[-20:])
        current_volume = volumes[-1]
        indicators['volume_ratio'] = current_volume / avg_volume if avg_volume > 0 else 1.0
        indicators['volume_spike'] = current_volume > avg_volume * 1.5

        return indicators

    def _evaluate_timeframe(
        self,
        indicators: Dict,
        closes: np.ndarray
    ) -> Tuple[str, int]:
        """
        Evaluate timeframe direction and strength

        Returns:
            Tuple of (direction, strength)
            direction: 'BULLISH', 'BEARISH', 'NEUTRAL'
            strength: 0-100
        """
        bullish_score = 0
        bearish_score = 0

        # EMA alignment (0-30 points)
        if indicators['above_ema_20']:
            bullish_score += 10
        else:
            bearish_score += 10

        if indicators['above_ema_50']:
            bullish_score += 10
        else:
            bearish_score += 10

        if indicators['above_ema_200']:
            bullish_score += 10
        else:
            bearish_score += 10

        # EMA trend (0-20 points)
        if indicators['ema_20_rising']:
            bullish_score += 10
        else:
            bearish_score += 10

        if indicators['ema_50_rising']:
            bullish_score += 10
        else:
            bearish_score += 10

        # MACD (0-15 points)
        if indicators['macd_bullish']:
            bullish_score += 15
        else:
            bearish_score += 15

        # RSI (0-15 points)
        rsi = indicators['rsi']
        if rsi > 50:
            bullish_score += int((rsi - 50) / 50 * 15)
        else:
            bearish_score += int((50 - rsi) / 50 * 15)

        # ADX (0-10 points) - strength multiplier
        if indicators['strong_trend']:
            strength_multiplier = min(1.5, indicators['adx'] / 25)
        else:
            strength_multiplier = 0.8

        # Volume confirmation (0-10 points)
        if indicators['volume_spike']:
            bullish_score += 10 if bullish_score > bearish_score else 0
            bearish_score += 10 if bearish_score > bullish_score else 0

        # Apply strength multiplier
        bullish_score = int(bullish_score * strength_multiplier)
        bearish_score = int(bearish_score * strength_multiplier)

        # Determine direction
        if bullish_score > bearish_score + 20:
            direction = 'BULLISH'
            strength = min(100, bullish_score)
        elif bearish_score > bullish_score + 20:
            direction = 'BEARISH'
            strength = min(100, bearish_score)
        else:
            direction = 'NEUTRAL'
            strength = max(bullish_score, bearish_score)

        return direction, strength

    def _calculate_confluence_score(self, signals: List[TimeframeSignal]) -> int:
        """
        Calculate weighted confluence score (0-100)

        Perfect alignment (all timeframes same direction) = 100
        Mixed signals = lower score

        Returns:
            Confluence score 0-100
        """
        if not signals:
            return 0

        # Count directions
        bullish_count = sum(1 for s in signals if s.direction == 'BULLISH')
        bearish_count = sum(1 for s in signals if s.direction == 'BEARISH')
        neutral_count = sum(1 for s in signals if s.direction == 'NEUTRAL')

        total = len(signals)

        # Calculate weighted score
        bullish_weight = 0
        bearish_weight = 0

        for signal in signals:
            tf_name = signal.timeframe
            weight = self.timeframes[tf_name]['weight']

            if signal.direction == 'BULLISH':
                bullish_weight += weight * (signal.strength / 100)
            elif signal.direction == 'BEARISH':
                bearish_weight += weight * (signal.strength / 100)

        # Normalize to 0-100
        max_weight = sum(tf['weight'] for tf in self.timeframes.values())

        if bullish_weight > bearish_weight:
            confluence = int((bullish_weight / max_weight) * 100)
        elif bearish_weight > bullish_weight:
            confluence = int((bearish_weight / max_weight) * 100)
        else:
            confluence = 0

        return min(100, confluence)

    def _determine_overall_direction(self, signals: List[TimeframeSignal]) -> str:
        """
        Determine overall direction from all timeframe signals

        Higher timeframes have more weight

        Returns:
            'BULLISH', 'BEARISH', or 'NEUTRAL'
        """
        if not signals:
            return 'NEUTRAL'

        bullish_weight = 0
        bearish_weight = 0

        for signal in signals:
            tf_name = signal.timeframe
            weight = self.timeframes[tf_name]['weight']

            if signal.direction == 'BULLISH':
                bullish_weight += weight
            elif signal.direction == 'BEARISH':
                bearish_weight += weight

        if bullish_weight > bearish_weight * 1.2:  # 20% threshold
            return 'BULLISH'
        elif bearish_weight > bullish_weight * 1.2:
            return 'BEARISH'
        else:
            return 'NEUTRAL'

    def _generate_signals(
        self,
        timeframe_signals: List[TimeframeSignal],
        confluence_score: int,
        overall_direction: str
    ) -> Dict:
        """
        Generate trading signals from confluence analysis

        Returns:
            Dict with bias, confidence, and reasoning
        """
        signals = {
            'bias': overall_direction,
            'confidence': confluence_score,
            'reasoning': [],
            'entry_recommendation': 'WAIT',
            'timeframe_alignment': {}
        }

        # Count aligned timeframes
        aligned = [s for s in timeframe_signals if s.direction == overall_direction]
        total = len(timeframe_signals)

        alignment_pct = (len(aligned) / total) * 100 if total > 0 else 0

        # HIGH CONFLUENCE (> 70) - strong signal
        if confluence_score >= 70:
            signals['entry_recommendation'] = 'ENTER'
            signals['reasoning'].append(
                f"High confluence ({confluence_score}/100) - {len(aligned)}/{total} timeframes aligned"
            )

            # Check which timeframes aligned
            for signal in aligned:
                signals['reasoning'].append(
                    f"{signal.timeframe}: {signal.direction} (strength: {signal.strength})"
                )

        # MODERATE CONFLUENCE (40-70) - wait for confirmation
        elif confluence_score >= 40:
            signals['entry_recommendation'] = 'WAIT_CONFIRMATION'
            signals['reasoning'].append(
                f"Moderate confluence ({confluence_score}/100) - wait for higher timeframe confirmation"
            )

            # Identify conflicting timeframes
            conflicting = [s for s in timeframe_signals if s.direction != overall_direction and s.direction != 'NEUTRAL']

            if conflicting:
                signals['reasoning'].append(
                    f"Conflicting signals: {', '.join([s.timeframe for s in conflicting])}"
                )

        # LOW CONFLUENCE (< 40) - no clear signal
        else:
            signals['entry_recommendation'] = 'WAIT'
            signals['reasoning'].append(
                f"Low confluence ({confluence_score}/100) - mixed signals across timeframes"
            )

        # Timeframe breakdown
        signals['timeframe_alignment'] = {
            'bullish': [s.timeframe for s in timeframe_signals if s.direction == 'BULLISH'],
            'bearish': [s.timeframe for s in timeframe_signals if s.direction == 'BEARISH'],
            'neutral': [s.timeframe for s in timeframe_signals if s.direction == 'NEUTRAL'],
        }

        return signals

    # Technical indicator helper functions

    def _ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average"""
        if len(data) < period:
            return np.full(len(data), data[0])

        multiplier = 2 / (period + 1)
        ema = np.zeros(len(data))
        ema[0] = data[0]

        for i in range(1, len(data)):
            ema[i] = (data[i] - ema[i-1]) * multiplier + ema[i-1]

        return ema

    def _rsi(self, data: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate Relative Strength Index"""
        if len(data) < period + 1:
            return np.full(len(data), 50.0)

        deltas = np.diff(data)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gains = np.zeros(len(data))
        avg_losses = np.zeros(len(data))

        avg_gains[period] = np.mean(gains[:period])
        avg_losses[period] = np.mean(losses[:period])

        for i in range(period + 1, len(data)):
            avg_gains[i] = (avg_gains[i-1] * (period - 1) + gains[i-1]) / period
            avg_losses[i] = (avg_losses[i-1] * (period - 1) + losses[i-1]) / period

        rs = np.where(avg_losses != 0, avg_gains / avg_losses, 0)
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _macd(
        self,
        data: np.ndarray,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Calculate MACD and signal line"""
        ema_fast = self._ema(data, fast)
        ema_slow = self._ema(data, slow)

        macd_line = ema_fast - ema_slow
        signal_line = self._ema(macd_line, signal)

        return macd_line, signal_line

    def _adx(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        period: int = 14
    ) -> np.ndarray:
        """Calculate Average Directional Index"""
        if len(highs) < period + 1:
            return np.full(len(highs), 25.0)

        # True Range
        tr = np.maximum(
            highs[1:] - lows[1:],
            np.maximum(
                np.abs(highs[1:] - closes[:-1]),
                np.abs(lows[1:] - closes[:-1])
            )
        )

        # Directional Movement
        dm_plus = np.where(
            (highs[1:] - highs[:-1]) > (lows[:-1] - lows[1:]),
            np.maximum(highs[1:] - highs[:-1], 0),
            0
        )

        dm_minus = np.where(
            (lows[:-1] - lows[1:]) > (highs[1:] - highs[:-1]),
            np.maximum(lows[:-1] - lows[1:], 0),
            0
        )

        # Smooth
        atr = self._ema(tr, period)
        di_plus = 100 * self._ema(dm_plus, period) / atr
        di_minus = 100 * self._ema(dm_minus, period) / atr

        # ADX
        dx = 100 * np.abs(di_plus - di_minus) / (di_plus + di_minus + 1e-10)
        adx = self._ema(dx, period)

        # Pad to match original length
        result = np.zeros(len(highs))
        result[1:] = adx

        return result

    def _atr(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        period: int = 14
    ) -> np.ndarray:
        """Calculate Average True Range"""
        if len(highs) < 2:
            return np.full(len(highs), 0.0)

        tr = np.maximum(
            highs[1:] - lows[1:],
            np.maximum(
                np.abs(highs[1:] - closes[:-1]),
                np.abs(lows[1:] - closes[:-1])
            )
        )

        atr = self._ema(tr, period)

        # Pad to match original length
        result = np.zeros(len(highs))
        result[1:] = atr

        return result


# Singleton instance
mtf_confluence = MultiTimeframeConfluence()
