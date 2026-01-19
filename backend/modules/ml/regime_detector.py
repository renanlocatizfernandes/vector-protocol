"""
Market Regime Detector using clustering algorithms
Detects different market conditions and maintains optimized configs for each
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sqlalchemy import select
import joblib
import os

from utils.logger import setup_logger
from models.database import SessionLocal
from api.models.ml_models import RegimeConfig
from modules.ml.feature_store import feature_store

logger = setup_logger("regime_detector")


class RegimeDetector:
    """
    Detects market regimes using clustering on market features
    """

    REGIMES = {
        0: 'trending_high_vol',    # Strong trend + high volatility
        1: 'trending_low_vol',     # Smooth trend + low volatility
        2: 'ranging_high_vol',     # Sideways + high volatility (dangerous)
        3: 'ranging_low_vol',      # Sideways + low volatility
        4: 'explosive',            # Breakouts / extreme events
    }

    MODEL_PATH = "models/regime_detector.pkl"

    def __init__(self, n_clusters: int = 5):
        self.n_clusters = n_clusters
        self.model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        self.scaler = StandardScaler()
        self.regime_configs = {}
        self.is_trained = False

        # Create models directory
        os.makedirs("models", exist_ok=True)

    async def fit_regimes(self, historical_data: pd.DataFrame):
        """
        Train clustering model on historical market data

        Args:
            historical_data: DataFrame with market features and outcomes
        """
        logger.info("🔄 Training regime detector...")

        if historical_data.empty or len(historical_data) < 100:
            logger.warning("Insufficient data for regime training, using defaults")
            await self._load_default_configs()
            return

        try:
            # Extract regime features
            features = self._extract_regime_features(historical_data)

            if features.empty:
                logger.warning("No valid features extracted, using defaults")
                await self._load_default_configs()
                return

            # Scale features
            X_scaled = self.scaler.fit_transform(features)

            # Fit clustering model
            self.model.fit(X_scaled)

            # Assign regimes to historical data
            historical_data['regime'] = self.model.labels_

            # Optimize parameters for each regime
            await self._optimize_regime_configs(historical_data)

            # Save model
            self._save_model()

            self.is_trained = True
            logger.info(f"✅ Regime detector trained with {len(historical_data)} samples")

        except Exception as e:
            logger.error(f"Error training regime detector: {e}")
            await self._load_default_configs()

    def _extract_regime_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract aggregated features for regime classification

        Returns features like:
        - Average ATR (volatility)
        - Average ADX (trend strength)
        - Volume coefficient of variation
        - Price range percentage
        """
        regime_features = []

        # Group by time windows (e.g., hourly or by symbol)
        # For simplicity, we'll use rolling windows
        window_size = 20

        for i in range(window_size, len(df)):
            window = df.iloc[i - window_size:i]

            features = {
                'atr_avg': window[['atr_1m', 'atr_5m', 'atr_1h']].mean().mean(),
                'adx_avg': window[['adx_1m', 'adx_5m', 'adx_1h']].mean().mean(),
                'volume_cv': window['volume_ratio'].std() / window['volume_ratio'].mean() if window['volume_ratio'].mean() > 0 else 0,
                'rsi_std': window[['rsi_1m', 'rsi_5m']].std().mean(),
                'trend_strength': abs(window['ema_slope_fast'].mean()),
            }

            regime_features.append(features)

        return pd.DataFrame(regime_features)

    async def _optimize_regime_configs(self, historical_data: pd.DataFrame):
        """
        For each regime, calculate optimal parameters based on performance
        """
        logger.info("⚙️ Optimizing configs for each regime...")

        with SessionLocal() as db:
            for regime_id in range(self.n_clusters):
                regime_data = historical_data[historical_data['regime'] == regime_id]

                if len(regime_data) < 10:
                    logger.warning(f"Regime {regime_id}: Insufficient data ({len(regime_data)} samples)")
                    continue

                # Calculate performance metrics
                wins = regime_data[regime_data['outcome'] == 'WIN']
                losses = regime_data[regime_data['outcome'] == 'LOSS']

                win_rate = len(wins) / len(regime_data) if len(regime_data) > 0 else 0.0
                avg_pnl = regime_data['pnl_pct'].mean()

                # Calculate Sharpe-like ratio
                sharpe = avg_pnl / regime_data['pnl_pct'].std() if regime_data['pnl_pct'].std() > 0 else 0.0

                # Optimize parameters based on regime characteristics
                config = self._generate_regime_config(regime_id, regime_data)

                # Store in database
                existing = db.execute(
                    select(RegimeConfig).where(RegimeConfig.regime_id == regime_id)
                ).scalar_one_or_none()

                if existing:
                    # Update existing
                    for key, value in config.items():
                        setattr(existing, key, value)
                    existing.win_rate = win_rate
                    existing.avg_pnl_pct = avg_pnl
                    existing.sharpe_ratio = sharpe
                    existing.n_samples = len(regime_data)
                    existing.trained_at = datetime.now()
                else:
                    # Create new
                    regime_config = RegimeConfig(
                        regime_id=regime_id,
                        regime_name=self.REGIMES[regime_id],
                        win_rate=win_rate,
                        avg_pnl_pct=avg_pnl,
                        sharpe_ratio=sharpe,
                        n_samples=len(regime_data),
                        **config
                    )
                    db.add(regime_config)

                db.commit()

                # Cache in memory
                self.regime_configs[regime_id] = config

                logger.info(f"  Regime {regime_id} ({self.REGIMES[regime_id]}): "
                           f"WinRate={win_rate:.1%}, Sharpe={sharpe:.2f}, N={len(regime_data)}")

    def _generate_regime_config(self, regime_id: int, regime_data: pd.DataFrame) -> Dict:
        """
        Generate optimized config for a specific regime based on its characteristics
        """
        # Calculate regime characteristics
        avg_volatility = regime_data[['atr_1m', 'atr_5m']].mean().mean()
        avg_trend = regime_data[['adx_1m', 'adx_5m']].mean().mean()
        avg_volume = regime_data['volume_ratio'].mean()

        # Base config
        config = {
            'min_score': 70,
            'max_positions': 15,
            'risk_per_trade_pct': 2.0,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'adx_min': 25,
            'volume_threshold_pct': 50.0,
            'stop_loss_atr_mult': 2.0,
            'take_profit_ratio': 2.0,
        }

        # Adjust based on regime
        if regime_id == 0:  # trending_high_vol
            config.update({
                'min_score': 65,
                'max_positions': 12,
                'risk_per_trade_pct': 1.8,
                'stop_loss_atr_mult': 2.5,
            })
        elif regime_id == 1:  # trending_low_vol
            config.update({
                'min_score': 70,
                'max_positions': 15,
                'risk_per_trade_pct': 2.0,
            })
        elif regime_id == 2:  # ranging_high_vol (dangerous)
            config.update({
                'min_score': 80,
                'max_positions': 8,
                'risk_per_trade_pct': 1.2,
                'adx_min': 30,
            })
        elif regime_id == 3:  # ranging_low_vol
            config.update({
                'min_score': 75,
                'max_positions': 10,
                'risk_per_trade_pct': 1.5,
            })
        elif regime_id == 4:  # explosive
            config.update({
                'min_score': 85,
                'max_positions': 5,
                'risk_per_trade_pct': 1.0,
                'stop_loss_atr_mult': 3.0,
            })

        return config

    async def detect_current_regime(self) -> int:
        """
        Detect current market regime based on recent data

        Returns:
            Regime ID (0-4)
        """
        if not self.is_trained:
            logger.warning("Regime detector not trained, loading from DB")
            await self._load_from_db()

        try:
            # Get recent market data (last hour)
            # For simplicity, use BTC as market indicator
            recent_features = await feature_store.get_historical_features(days=1)

            if recent_features.empty:
                logger.warning("No recent data for regime detection, using default (regime 1)")
                return 1

            # Extract regime features from recent data
            regime_features = self._extract_regime_features(recent_features)

            if regime_features.empty:
                return 1

            # Use last window
            current_features = regime_features.iloc[-1:].values

            # Scale and predict
            X_scaled = self.scaler.transform(current_features)
            regime = self.model.predict(X_scaled)[0]

            logger.info(f"📍 Detected regime: {self.REGIMES[regime]} (ID={regime})")
            return int(regime)

        except Exception as e:
            logger.error(f"Error detecting regime: {e}")
            return 1  # Default to trending_low_vol

    def get_regime_config(self, regime: int) -> Dict:
        """
        Get optimized config for a specific regime

        Args:
            regime: Regime ID (0-4)

        Returns:
            Dictionary of optimized parameters
        """
        if regime in self.regime_configs:
            return self.regime_configs[regime]

        # Load from DB if not in cache
        try:
            with SessionLocal() as db:
                config = db.execute(
                    select(RegimeConfig).where(RegimeConfig.regime_id == regime)
                ).scalar_one_or_none()

                if config:
                    params = {
                        'min_score': config.min_score,
                        'max_positions': config.max_positions,
                        'risk_per_trade_pct': config.risk_per_trade_pct,
                        'rsi_oversold': config.rsi_oversold,
                        'rsi_overbought': config.rsi_overbought,
                        'adx_min': config.adx_min,
                        'volume_threshold_pct': config.volume_threshold_pct,
                        'stop_loss_atr_mult': config.stop_loss_atr_mult,
                        'take_profit_ratio': config.take_profit_ratio,
                    }
                    self.regime_configs[regime] = params
                    return params

        except Exception as e:
            logger.error(f"Error loading regime config: {e}")

        # Return default if not found
        return self._get_default_config()

    async def _load_default_configs(self):
        """Load default configurations for all regimes"""
        logger.info("📦 Loading default regime configs")

        default_configs = {
            0: {'min_score': 65, 'max_positions': 12, 'risk_per_trade_pct': 1.8},
            1: {'min_score': 70, 'max_positions': 15, 'risk_per_trade_pct': 2.0},
            2: {'min_score': 80, 'max_positions': 8, 'risk_per_trade_pct': 1.2},
            3: {'min_score': 75, 'max_positions': 10, 'risk_per_trade_pct': 1.5},
            4: {'min_score': 85, 'max_positions': 5, 'risk_per_trade_pct': 1.0},
        }

        for regime_id, config in default_configs.items():
            self.regime_configs[regime_id] = {**self._get_default_config(), **config}

        self.is_trained = True

    def _get_default_config(self) -> Dict:
        """Get default trading config"""
        return {
            'min_score': 70,
            'max_positions': 15,
            'risk_per_trade_pct': 2.0,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'adx_min': 25,
            'volume_threshold_pct': 50.0,
            'stop_loss_atr_mult': 2.0,
            'take_profit_ratio': 2.0,
        }

    async def _load_from_db(self):
        """Load trained model and configs from database"""
        try:
            # Load model from file
            if os.path.exists(self.MODEL_PATH):
                saved_data = joblib.load(self.MODEL_PATH)
                self.model = saved_data['model']
                self.scaler = saved_data['scaler']
                logger.info("✅ Loaded regime detector model from disk")

            # Load configs from DB
            with SessionLocal() as db:
                configs = db.execute(select(RegimeConfig)).scalars().all()

                for config in configs:
                    self.regime_configs[config.regime_id] = {
                        'min_score': config.min_score,
                        'max_positions': config.max_positions,
                        'risk_per_trade_pct': config.risk_per_trade_pct,
                        'rsi_oversold': config.rsi_oversold,
                        'rsi_overbought': config.rsi_overbought,
                        'adx_min': config.adx_min,
                        'volume_threshold_pct': config.volume_threshold_pct,
                        'stop_loss_atr_mult': config.stop_loss_atr_mult,
                        'take_profit_ratio': config.take_profit_ratio,
                    }

            if self.regime_configs:
                self.is_trained = True
                logger.info(f"✅ Loaded {len(self.regime_configs)} regime configs from DB")
            else:
                await self._load_default_configs()

        except Exception as e:
            logger.error(f"Error loading from DB: {e}")
            await self._load_default_configs()

    def _save_model(self):
        """Save trained model to disk"""
        try:
            saved_data = {
                'model': self.model,
                'scaler': self.scaler,
                'n_clusters': self.n_clusters,
            }
            joblib.dump(saved_data, self.MODEL_PATH)
            logger.info(f"💾 Saved regime detector model to {self.MODEL_PATH}")

        except Exception as e:
            logger.error(f"Error saving model: {e}")


# Singleton instance
regime_detector = RegimeDetector()
