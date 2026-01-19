"""
Adaptive Intelligence Engine
Main orchestrator for all ML components
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, List

from utils.logger import setup_logger
from modules.ml.feature_store import feature_store
from modules.ml.regime_detector import regime_detector
from modules.ml.indicator_optimizer import indicator_optimizer
from modules.ml.adaptive_controller import adaptive_controller
from modules.ml.anomaly_detector import anomaly_detector

logger = setup_logger("adaptive_engine")


class AdaptiveIntelligenceEngine:
    """
    Orchestrates all ML components for autonomous trading optimization
    """

    def __init__(self):
        self.feature_store = feature_store
        self.regime_detector = regime_detector
        self.indicator_optimizer = indicator_optimizer
        self.adaptive_controller = adaptive_controller
        self.anomaly_detector = anomaly_detector

        self.current_regime = None
        self.current_config = None
        self.is_initialized = False
        self.trades_since_retrain = 0

    async def initialize(self, historical_days: int = 90):
        """
        Initialize the Adaptive Intelligence Engine with historical data

        Args:
            historical_days: Number of days of historical data to use for training
        """
        logger.info("=" * 70)
        logger.info("🧠 INITIALIZING ADAPTIVE INTELLIGENCE ENGINE")
        logger.info("=" * 70)

        try:
            # Step 1: Load historical features
            logger.info(f"\n📊 Step 1/5: Loading {historical_days} days of historical data...")
            historical_data = await self.feature_store.get_historical_features(days=historical_days)

            if historical_data.empty or len(historical_data) < 100:
                logger.warning(f"⚠️ Insufficient historical data ({len(historical_data)} samples)")
                logger.info("   Using default configurations...")
                await self._initialize_defaults()
                return

            logger.info(f"   ✅ Loaded {len(historical_data)} trade samples")

            # Step 2: Train regime detector
            logger.info("\n📍 Step 2/5: Training market regime detector...")
            await self.regime_detector.fit_regimes(historical_data)
            logger.info("   ✅ Regime detector trained")

            # Step 3: Train indicator optimizer
            logger.info("\n⚖️ Step 3/5: Training indicator weight optimizer...")

            # Prepare features and labels
            features = historical_data[indicator_optimizer.FEATURE_COLUMNS].copy()
            labels = (historical_data['outcome'] == 'WIN').astype(int)

            if len(labels.unique()) < 2:
                logger.warning("   ⚠️ Insufficient class diversity, skipping ML training")
            else:
                train_result = await self.indicator_optimizer.train(features, labels)

                if 'error' not in train_result:
                    logger.info("   ✅ Indicator optimizer trained")
                    logger.info(f"      Best AUC: {max([m['auc'] for m in train_result['metrics'].values()]):.3f}")
                else:
                    logger.warning(f"   ⚠️ Training failed: {train_result.get('error')}")

            # Step 4: Detect anomalies and mine patterns
            logger.info("\n🔍 Step 4/5: Detecting anomalies and mining loss patterns...")

            losing_trades = historical_data[historical_data['outcome'] == 'LOSS']

            if len(losing_trades) >= 50:
                anomalies = await self.anomaly_detector.detect_anomalies(losing_trades)
                filter_rules = await self.anomaly_detector.mine_loss_patterns(anomalies)

                logger.info(f"   ✅ Found {len(filter_rules)} filter rules")
            else:
                logger.info(f"   ⚠️ Insufficient losing trades ({len(losing_trades)})")

            # Step 5: Load active filter rules
            logger.info("\n📥 Step 5/5: Loading active filter rules...")
            await self.anomaly_detector.load_active_rules()

            self.is_initialized = True
            self.trades_since_retrain = 0

            logger.info("\n" + "=" * 70)
            logger.info("✅ ADAPTIVE INTELLIGENCE ENGINE INITIALIZED SUCCESSFULLY")
            logger.info("=" * 70)

        except Exception as e:
            logger.error(f"❌ Error initializing Adaptive Engine: {e}", exc_info=True)
            logger.info("   Falling back to default configurations...")
            await self._initialize_defaults()

    async def _initialize_defaults(self):
        """Initialize with default configs when insufficient data"""
        await self.regime_detector._load_default_configs()
        self.is_initialized = True
        logger.info("✅ Initialized with default configurations")

    async def get_adaptive_config(self) -> Dict:
        """
        Get dynamically optimized configuration for current market conditions

        Returns:
            Dictionary with optimized trading parameters and indicator weights
        """
        if not self.is_initialized:
            logger.warning("Engine not initialized, initializing now...")
            await self.initialize()

        try:
            # Step 1: Detect current market regime
            logger.info("🔄 Getting adaptive configuration...")

            self.current_regime = await self.regime_detector.detect_current_regime()
            regime_name = self.regime_detector.REGIMES[self.current_regime]

            logger.info(f"   📍 Current regime: {regime_name} (ID={self.current_regime})")

            # Step 2: Get base config for this regime
            regime_config = self.regime_detector.get_regime_config(self.current_regime)

            # Step 3: Calculate recent performance metrics
            recent_metrics = await self.adaptive_controller.calculate_recent_metrics(days=7)

            logger.info(f"   📈 Recent performance: "
                       f"Sharpe={recent_metrics['sharpe_ratio_7d']:.2f}, "
                       f"WinRate={recent_metrics['win_rate_7d']:.1%}, "
                       f"Trades={recent_metrics['n_trades']}")

            # Step 4: Apply PID adjustments
            pid_adjustments = await self.adaptive_controller.apply_pid_adjustments(recent_metrics)

            # Step 5: Merge configs
            final_config = {**regime_config, **pid_adjustments}

            # Step 6: Add indicator weights
            final_config['indicator_weights'] = self.indicator_optimizer.get_dynamic_weights()

            # Step 7: Add metadata
            final_config['regime_id'] = self.current_regime
            final_config['regime_name'] = regime_name
            final_config['recent_metrics'] = recent_metrics

            self.current_config = final_config

            logger.info(f"   ✅ Config updated: "
                       f"MinScore={final_config['min_score']}, "
                       f"MaxPos={final_config['max_positions']}, "
                       f"Risk={final_config['risk_per_trade_pct']:.1f}%")

            return final_config

        except Exception as e:
            logger.error(f"Error getting adaptive config: {e}", exc_info=True)
            return self._get_fallback_config()

    async def evaluate_trade_opportunity(
        self,
        symbol: str,
        base_signal: Dict
    ) -> Dict:
        """
        Evaluate trade opportunity using ML ensemble and filter rules

        Args:
            symbol: Trading symbol
            base_signal: Traditional signal analysis result

        Returns:
            Dictionary with ML evaluation and final decision
        """
        try:
            # Step 1: Compute current features
            features = await self.feature_store.compute_features(symbol)

            if not features:
                return {
                    'action': 'SKIP',
                    'reason': 'Feature computation failed',
                    'ml_score': 0.0
                }

            # Step 2: Check against blacklist rules
            matches_rule, matched_rule = self.anomaly_detector.matches_blacklist_rule(features)

            if matches_rule:
                return {
                    'action': 'SKIP',
                    'reason': f'Matches loss pattern: {matched_rule["rule_name"]}',
                    'ml_score': 0.0,
                    'matched_rule': matched_rule
                }

            # Step 3: ML prediction
            ml_probability = await self.indicator_optimizer.predict_trade_quality(features)

            # Convert to 0-100 scale
            ml_score = ml_probability * 100

            # Step 4: Get traditional score from base signal
            traditional_score = base_signal.get('score', base_signal.get('confidence', 50))

            # Step 5: Combine scores (70% ML, 30% traditional)
            final_score = (ml_score * 0.70) + (traditional_score * 0.30)

            # Step 6: Get dynamic weights for context
            weights = self.indicator_optimizer.get_dynamic_weights()
            top_indicators = sorted(weights.items(), key=lambda x: x[1], reverse=True)[:3]

            # Step 7: Decision
            min_score = self.current_config.get('min_score', 70)
            action = 'EXECUTE' if final_score >= min_score else 'SKIP'

            result = {
                'action': action,
                'ml_score': ml_score,
                'traditional_score': traditional_score,
                'final_score': final_score,
                'min_score_threshold': min_score,
                'regime': self.regime_detector.REGIMES[self.current_regime],
                'top_indicators': [ind[0] for ind in top_indicators],
                'features_snapshot': features,
            }

            if action == 'SKIP':
                result['reason'] = f'Score {final_score:.1f} below threshold {min_score}'

            return result

        except Exception as e:
            logger.error(f"Error evaluating trade opportunity: {e}", exc_info=True)
            return {
                'action': 'SKIP',
                'reason': f'Evaluation error: {str(e)}',
                'ml_score': 0.0
            }

    async def record_trade_outcome(
        self,
        trade_id: str,
        symbol: str,
        outcome: Dict,
        features: Optional[Dict] = None
    ):
        """
        Record trade outcome for continuous learning

        Args:
            trade_id: Unique trade identifier
            symbol: Trading symbol
            outcome: Dict with 'outcome' ('WIN'/'LOSS'), 'pnl_pct', etc.
            features: Optional pre-computed features
        """
        try:
            # Get features if not provided
            if features is None:
                features = await self.feature_store.compute_features(symbol)

            # Add regime to features
            if features:
                features['market_regime'] = self.current_regime

            # Store in database
            await self.feature_store.store_trade_outcome(trade_id, features, outcome)

            # Increment counter
            self.trades_since_retrain += 1

            # Auto-retrain every 100 trades
            if self.trades_since_retrain >= 100:
                logger.info("🔄 Auto-triggering model retraining (100 new trades)")
                await self.retrain_models()

        except Exception as e:
            logger.error(f"Error recording trade outcome: {e}")

    async def retrain_models(self, lookback_days: int = 30):
        """
        Retrain ML models with recent data (online learning)

        Args:
            lookback_days: Number of days of recent data to use
        """
        logger.info("=" * 70)
        logger.info("🔄 RETRAINING ML MODELS")
        logger.info("=" * 70)

        try:
            # Load recent data
            recent_data = await self.feature_store.get_historical_features(days=lookback_days)

            if len(recent_data) < 100:
                logger.warning(f"Insufficient data for retraining ({len(recent_data)} samples)")
                return

            logger.info(f"📊 Training with {len(recent_data)} recent samples")

            # Retrain indicator optimizer
            features = recent_data[indicator_optimizer.FEATURE_COLUMNS].copy()
            labels = (recent_data['outcome'] == 'WIN').astype(int)

            if len(labels.unique()) >= 2:
                logger.info("⚖️ Retraining indicator optimizer...")
                train_result = await self.indicator_optimizer.train(features, labels)

                if 'error' not in train_result:
                    logger.info(f"   ✅ Retrained with AUC: "
                              f"{max([m['auc'] for m in train_result['metrics'].values()]):.3f}")

            # Re-optimize parameters for each regime
            logger.info("⚙️ Re-optimizing regime parameters...")
            for regime_id in range(5):
                optimal_params = await self.adaptive_controller.optimize_parameters(
                    regime_id,
                    lookback_days=lookback_days,
                    n_calls=20  # Fewer calls for faster retraining
                )
                self.regime_detector.regime_configs[regime_id] = optimal_params

            logger.info("   ✅ Parameters re-optimized")

            # Reset counter
            self.trades_since_retrain = 0

            logger.info("=" * 70)
            logger.info("✅ RETRAINING COMPLETED")
            logger.info("=" * 70)

        except Exception as e:
            logger.error(f"Error retraining models: {e}", exc_info=True)

    def _get_fallback_config(self) -> Dict:
        """Get fallback configuration in case of errors"""
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
            'indicator_weights': {},
            'regime_id': 1,
            'regime_name': 'fallback',
        }

    async def get_status(self) -> Dict:
        """Get current status of the Adaptive Intelligence Engine"""
        return {
            'is_initialized': self.is_initialized,
            'current_regime': {
                'id': self.current_regime,
                'name': self.regime_detector.REGIMES.get(self.current_regime, 'unknown')
            } if self.current_regime is not None else None,
            'trades_since_retrain': self.trades_since_retrain,
            'models_trained': {
                'regime_detector': self.regime_detector.is_trained,
                'indicator_optimizer': self.indicator_optimizer.is_trained,
                'anomaly_detector': self.anomaly_detector.is_trained,
            },
            'active_filter_rules': len(self.anomaly_detector.blacklist_rules),
            'current_config': self.current_config,
        }


# Singleton instance
adaptive_engine = AdaptiveIntelligenceEngine()
