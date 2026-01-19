"""
Indicator Weight Optimizer using Ensemble Machine Learning
Learns which indicators are most predictive and adjusts weights dynamically
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import xgboost as xgb
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score, precision_score, recall_score, f1_score
import joblib
import os

from utils.logger import setup_logger
from models.database import SessionLocal
from api.models.ml_models import MLModelMetadata, IndicatorWeightsHistory
from modules.ml.feature_store import feature_store

logger = setup_logger("indicator_optimizer")


class IndicatorWeightOptimizer:
    """
    Ensemble ML model that predicts trade success and learns indicator importance
    """

    FEATURE_COLUMNS = [
        # Volatility
        'atr_1m', 'atr_5m', 'atr_1h',
        'bb_width_1m', 'bb_width_5m',

        # Trend
        'adx_1m', 'adx_5m', 'adx_1h',
        'ema_slope_fast', 'ema_slope_slow',

        # Momentum
        'rsi_1m', 'rsi_5m', 'rsi_1h',
        'macd_histogram',

        # Volume
        'volume_ratio', 'volume_trend',
        'vwap_distance', 'vwap_slope',

        # Context
        'market_hour', 'day_of_week',
        'spread_bps',
    ]

    MODEL_DIR = "models/indicator_optimizer"

    def __init__(self):
        self.models = {
            'xgboost': xgb.XGBClassifier(
                max_depth=6,
                n_estimators=100,
                learning_rate=0.1,
                random_state=42,
                eval_metric='logloss'
            ),
            'random_forest': RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            ),
            'logistic': LogisticRegression(
                max_iter=1000,
                random_state=42,
                n_jobs=-1
            )
        }

        self.ensemble_weights = [0.5, 0.3, 0.2]  # XGBoost gets highest weight
        self.indicator_importance = {}
        self.is_trained = False
        self.version = "1.0"

        # Create models directory
        os.makedirs(self.MODEL_DIR, exist_ok=True)

    async def train(
        self,
        features: pd.DataFrame,
        labels: pd.Series,
        test_size: float = 0.2
    ) -> Dict:
        """
        Train ensemble of models

        Args:
            features: DataFrame with indicator features
            labels: Series with binary labels (1=WIN, 0=LOSS)
            test_size: Proportion of data for testing

        Returns:
            Dictionary with training metrics
        """
        logger.info(f"🔄 Training indicator optimizer with {len(features)} samples...")

        if len(features) < 100:
            logger.warning("Insufficient data for training")
            return {'error': 'insufficient_data'}

        try:
            # Prepare data
            X = features[self.FEATURE_COLUMNS].fillna(0)
            y = labels

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42, stratify=y
            )

            logger.info(f"  Train: {len(X_train)}, Test: {len(X_test)}")
            logger.info(f"  Class distribution: {y_train.value_counts().to_dict()}")

            # Train each model
            metrics = {}

            for name, model in self.models.items():
                logger.info(f"  Training {name}...")

                model.fit(X_train, y_train)

                # Predictions
                y_pred = model.predict(X_test)
                y_pred_proba = model.predict_proba(X_test)[:, 1]

                # Calculate metrics
                metrics[name] = {
                    'accuracy': accuracy_score(y_test, y_pred),
                    'auc': roc_auc_score(y_test, y_pred_proba),
                    'precision': precision_score(y_test, y_pred, zero_division=0),
                    'recall': recall_score(y_test, y_pred, zero_division=0),
                    'f1': f1_score(y_test, y_pred, zero_division=0),
                }

                logger.info(f"    {name}: AUC={metrics[name]['auc']:.3f}, "
                           f"Accuracy={metrics[name]['accuracy']:.3f}")

            # Extract feature importance
            self._calculate_indicator_importance(X)

            # Save models
            await self._save_models(metrics)

            # Store metadata in DB
            await self._save_model_metadata(metrics, len(X_train), len(X_test))

            self.is_trained = True

            logger.info("✅ Training completed")

            return {
                'status': 'success',
                'metrics': metrics,
                'n_train': len(X_train),
                'n_test': len(X_test),
            }

        except Exception as e:
            logger.error(f"Error training models: {e}", exc_info=True)
            return {'error': str(e)}

    def _calculate_indicator_importance(self, features: pd.DataFrame):
        """
        Calculate and combine feature importance from RF and XGBoost
        """
        try:
            rf_importance = self.models['random_forest'].feature_importances_
            xgb_importance = self.models['xgboost'].feature_importances_

            # Weighted combination (XGBoost gets more weight)
            combined = (xgb_importance * 0.6 + rf_importance * 0.4)

            # Normalize to sum to 1.0
            combined = combined / combined.sum()

            # Map to feature names
            for idx, col in enumerate(self.FEATURE_COLUMNS):
                self.indicator_importance[col] = float(combined[idx])

            # Log top indicators
            sorted_importance = sorted(
                self.indicator_importance.items(),
                key=lambda x: x[1],
                reverse=True
            )

            logger.info("📊 Top 5 Indicators:")
            for name, importance in sorted_importance[:5]:
                logger.info(f"  {name}: {importance:.4f}")

        except Exception as e:
            logger.error(f"Error calculating importance: {e}")

    async def predict_trade_quality(self, features: Dict) -> float:
        """
        Predict probability of trade success using ensemble

        Args:
            features: Dictionary of indicator values

        Returns:
            Probability of success (0.0 to 1.0)
        """
        if not self.is_trained:
            logger.warning("Models not trained, loading from disk")
            await self._load_models()

        try:
            # Prepare features
            feature_values = {k: features.get(k, 0.0) for k in self.FEATURE_COLUMNS}
            X = pd.DataFrame([feature_values])

            # Get predictions from each model
            predictions = []

            for model_name, model in self.models.items():
                try:
                    pred_proba = model.predict_proba(X)[0][1]  # Probability of class 1 (WIN)
                    predictions.append(pred_proba)
                except Exception as e:
                    logger.warning(f"Error predicting with {model_name}: {e}")
                    predictions.append(0.5)  # Neutral

            # Weighted ensemble
            ensemble_score = np.average(predictions, weights=self.ensemble_weights)

            return float(ensemble_score)

        except Exception as e:
            logger.error(f"Error predicting trade quality: {e}")
            return 0.5  # Neutral if error

    def get_dynamic_weights(self) -> Dict[str, float]:
        """
        Get normalized weights for each indicator

        Returns:
            Dictionary mapping indicator name to weight (sums to 1.0)
        """
        if not self.indicator_importance:
            logger.warning("Indicator importance not calculated, returning uniform weights")
            n = len(self.FEATURE_COLUMNS)
            return {col: 1.0 / n for col in self.FEATURE_COLUMNS}

        return self.indicator_importance.copy()

    async def _save_models(self, metrics: Dict):
        """Save trained models to disk"""
        try:
            for name, model in self.models.items():
                model_path = os.path.join(self.MODEL_DIR, f"{name}_v{self.version}.pkl")
                joblib.dump(model, model_path)

            # Save importance and weights
            metadata = {
                'indicator_importance': self.indicator_importance,
                'ensemble_weights': self.ensemble_weights,
                'version': self.version,
                'feature_columns': self.FEATURE_COLUMNS,
            }

            metadata_path = os.path.join(self.MODEL_DIR, f"metadata_v{self.version}.pkl")
            joblib.dump(metadata, metadata_path)

            logger.info(f"💾 Models saved to {self.MODEL_DIR}")

        except Exception as e:
            logger.error(f"Error saving models: {e}")

    async def _load_models(self):
        """Load trained models from disk"""
        try:
            # Find latest version
            metadata_path = os.path.join(self.MODEL_DIR, f"metadata_v{self.version}.pkl")

            if not os.path.exists(metadata_path):
                logger.warning("No saved models found")
                return

            # Load metadata
            metadata = joblib.load(metadata_path)
            self.indicator_importance = metadata['indicator_importance']
            self.ensemble_weights = metadata['ensemble_weights']
            self.version = metadata['version']

            # Load models
            for name in self.models.keys():
                model_path = os.path.join(self.MODEL_DIR, f"{name}_v{self.version}.pkl")
                if os.path.exists(model_path):
                    self.models[name] = joblib.load(model_path)

            self.is_trained = True
            logger.info(f"✅ Loaded models version {self.version}")

        except Exception as e:
            logger.error(f"Error loading models: {e}")

    async def _save_model_metadata(self, metrics: Dict, n_train: int, n_test: int):
        """Save model metadata to database"""
        try:
            with SessionLocal() as db:
                for model_name, model_metrics in metrics.items():
                    metadata = MLModelMetadata(
                        model_name=f"indicator_optimizer_{model_name}",
                        model_type=model_name,
                        version=self.version,
                        model_path=os.path.join(self.MODEL_DIR, f"{model_name}_v{self.version}.pkl"),
                        auc_score=model_metrics['auc'],
                        accuracy=model_metrics['accuracy'],
                        precision_score=model_metrics['precision'],
                        recall_score=model_metrics['recall'],
                        f1_score=model_metrics['f1'],
                        n_samples_train=n_train,
                        n_samples_test=n_test,
                        features_used=self.FEATURE_COLUMNS,
                        hyperparameters={},
                        is_active=True,
                    )
                    db.add(metadata)

                # Save indicator weights history
                weights_history = IndicatorWeightsHistory(
                    weights_json=self.indicator_importance,
                    n_trades_evaluated=n_train + n_test,
                )
                db.add(weights_history)

                db.commit()

            logger.info("💾 Model metadata saved to database")

        except Exception as e:
            logger.error(f"Error saving model metadata: {e}")

    async def get_feature_importance_report(self) -> Dict:
        """
        Generate detailed feature importance report

        Returns:
            Dictionary with importance metrics and recommendations
        """
        if not self.indicator_importance:
            return {'error': 'no_importance_data'}

        # Sort by importance
        sorted_importance = sorted(
            self.indicator_importance.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Categorize by feature type
        categories = {
            'volatility': [],
            'trend': [],
            'momentum': [],
            'volume': [],
            'context': [],
        }

        for feature, importance in sorted_importance:
            if 'atr' in feature or 'bb' in feature:
                categories['volatility'].append((feature, importance))
            elif 'adx' in feature or 'ema' in feature:
                categories['trend'].append((feature, importance))
            elif 'rsi' in feature or 'macd' in feature:
                categories['momentum'].append((feature, importance))
            elif 'volume' in feature or 'vwap' in feature:
                categories['volume'].append((feature, importance))
            else:
                categories['context'].append((feature, importance))

        # Calculate category totals
        category_totals = {
            cat: sum(imp for _, imp in features)
            for cat, features in categories.items()
        }

        return {
            'all_features': dict(sorted_importance),
            'by_category': categories,
            'category_totals': category_totals,
            'top_5': dict(sorted_importance[:5]),
            'bottom_5': dict(sorted_importance[-5:]),
        }


# Singleton instance
indicator_optimizer = IndicatorWeightOptimizer()
