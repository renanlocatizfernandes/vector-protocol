"""
Anomaly Detector and Pattern Miner
Detects losing trade patterns and generates filter rules
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple
from sklearn.ensemble import IsolationForest
from mlxtend.frequent_patterns import apriori, association_rules
from sqlalchemy import select

from utils.logger import setup_logger
from models.database import SessionLocal
from api.models.ml_models import FilterRule
from modules.ml.feature_store import feature_store

logger = setup_logger("anomaly_detector")


class AnomalyDetector:
    """
    Detects anomalous losing trades and mines patterns for filter rules
    """

    FEATURE_COLUMNS = [
        'rsi_1m', 'rsi_5m', 'adx_1m', 'volume_ratio',
        'spread_bps', 'bb_width_1m', 'macd_histogram'
    ]

    def __init__(self):
        self.isolation_forest = IsolationForest(
            contamination=0.15,  # 15% of trades are outliers
            random_state=42,
            n_estimators=100
        )
        self.blacklist_rules = []
        self.is_trained = False

    async def detect_anomalies(self, trades_df: pd.DataFrame) -> pd.DataFrame:
        """
        Identify anomalous losing trades using Isolation Forest

        Args:
            trades_df: DataFrame with trade features

        Returns:
            DataFrame containing only anomalous trades
        """
        logger.info(f"🔍 Detecting anomalies in {len(trades_df)} trades...")

        if trades_df.empty or len(trades_df) < 50:
            logger.warning("Insufficient data for anomaly detection")
            return pd.DataFrame()

        try:
            # Select features for anomaly detection
            available_features = [col for col in self.FEATURE_COLUMNS if col in trades_df.columns]

            if not available_features:
                logger.warning("No valid features for anomaly detection")
                return pd.DataFrame()

            features = trades_df[available_features].fillna(0)

            # Fit and predict
            trades_df['anomaly'] = self.isolation_forest.fit_predict(features)

            # -1 = anomaly, 1 = normal
            anomalous_trades = trades_df[trades_df['anomaly'] == -1].copy()

            logger.info(f"  Found {len(anomalous_trades)} anomalous trades "
                       f"({len(anomalous_trades)/len(trades_df)*100:.1f}%)")

            self.is_trained = True
            return anomalous_trades

        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}", exc_info=True)
            return pd.DataFrame()

    async def mine_loss_patterns(
        self,
        losing_trades: pd.DataFrame,
        min_support: float = 0.15,
        min_confidence: float = 0.75
    ) -> List[Dict]:
        """
        Mine association rules from losing trades to create filter rules

        Args:
            losing_trades: DataFrame with losing trades
            min_support: Minimum support for frequent itemsets
            min_confidence: Minimum confidence for rules

        Returns:
            List of filter rule dictionaries
        """
        logger.info(f"⛏️ Mining patterns from {len(losing_trades)} losing trades...")

        if losing_trades.empty or len(losing_trades) < 20:
            logger.warning("Insufficient data for pattern mining")
            return []

        try:
            # Discretize features into bins
            df_binned = self._discretize_features(losing_trades)

            if df_binned.empty:
                logger.warning("No features to discretize")
                return []

            # Apply Apriori algorithm
            frequent_itemsets = apriori(
                df_binned,
                min_support=min_support,
                use_colnames=True,
                max_len=3  # Max 3 conditions per rule
            )

            if frequent_itemsets.empty:
                logger.info("  No frequent itemsets found")
                return []

            logger.info(f"  Found {len(frequent_itemsets)} frequent itemsets")

            # Generate association rules
            rules = association_rules(
                frequent_itemsets,
                metric="confidence",
                min_threshold=min_confidence
            )

            if rules.empty:
                logger.info("  No association rules found")
                return []

            # Filter for significant rules
            significant_rules = rules[
                (rules['confidence'] >= min_confidence) &
                (rules['lift'] > 1.5) &
                (rules['support'] >= min_support)
            ].copy()

            logger.info(f"  Found {len(significant_rules)} significant rules")

            # Convert to filter rules
            filter_rules = self._convert_to_filter_rules(significant_rules)

            # Save to database
            await self._save_filter_rules(filter_rules)

            return filter_rules

        except Exception as e:
            logger.error(f"Error mining patterns: {e}", exc_info=True)
            return []

    def _discretize_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert continuous features to binary (True/False) conditions

        Returns DataFrame suitable for Apriori algorithm
        """
        binned = pd.DataFrame()

        try:
            # RSI conditions
            if 'rsi_1m' in df.columns:
                binned['rsi_1m_overbought'] = df['rsi_1m'] > 75
                binned['rsi_1m_oversold'] = df['rsi_1m'] < 25
                binned['rsi_1m_extreme'] = (df['rsi_1m'] > 80) | (df['rsi_1m'] < 20)

            if 'rsi_5m' in df.columns:
                binned['rsi_5m_overbought'] = df['rsi_5m'] > 70
                binned['rsi_5m_oversold'] = df['rsi_5m'] < 30

            # Volume conditions
            if 'volume_ratio' in df.columns:
                binned['volume_low'] = df['volume_ratio'] < 0.5
                binned['volume_very_low'] = df['volume_ratio'] < 0.3
                binned['volume_high'] = df['volume_ratio'] > 2.0

            # ADX conditions
            if 'adx_1m' in df.columns:
                binned['adx_weak'] = df['adx_1m'] < 20
                binned['adx_very_weak'] = df['adx_1m'] < 15
                binned['adx_strong'] = df['adx_1m'] > 40

            # Spread conditions
            if 'spread_bps' in df.columns:
                binned['spread_wide'] = df['spread_bps'] > 10
                binned['spread_very_wide'] = df['spread_bps'] > 20

            # Volatility conditions
            if 'bb_width_1m' in df.columns:
                bb_median = df['bb_width_1m'].median()
                binned['volatility_high'] = df['bb_width_1m'] > bb_median * 1.5
                binned['volatility_low'] = df['bb_width_1m'] < bb_median * 0.5

            # MACD conditions
            if 'macd_histogram' in df.columns:
                binned['macd_negative'] = df['macd_histogram'] < 0
                binned['macd_very_negative'] = df['macd_histogram'] < -0.01

            # Time-based conditions
            if 'market_hour' in df.columns:
                binned['asian_hours'] = df['market_hour'].isin([0, 1, 2, 3, 4, 5, 6, 7, 8])
                binned['us_hours'] = df['market_hour'].isin([13, 14, 15, 16, 17, 18, 19, 20])

            if 'day_of_week' in df.columns:
                binned['weekend_approaching'] = df['day_of_week'].isin([4, 5, 6])  # Fri, Sat, Sun

            return binned

        except Exception as e:
            logger.error(f"Error discretizing features: {e}")
            return pd.DataFrame()

    def _convert_to_filter_rules(self, rules_df: pd.DataFrame) -> List[Dict]:
        """
        Convert association rules to executable filter rules
        """
        filter_rules = []

        for idx, rule in rules_df.iterrows():
            try:
                antecedents = list(rule['antecedents'])

                # Create human-readable rule description
                conditions_str = " AND ".join(antecedents)

                rule_dict = {
                    'rule_name': f"Filter_{idx}",
                    'conditions': antecedents,
                    'conditions_str': conditions_str,
                    'action': 'SKIP_TRADE',
                    'confidence': float(rule['confidence']),
                    'support': float(rule['support']),
                    'lift': float(rule['lift']),
                }

                filter_rules.append(rule_dict)

            except Exception as e:
                logger.warning(f"Error converting rule {idx}: {e}")
                continue

        return filter_rules

    async def _save_filter_rules(self, filter_rules: List[Dict]):
        """Save filter rules to database"""
        try:
            with SessionLocal() as db:
                for rule in filter_rules:
                    # Check if rule already exists
                    existing = db.execute(
                        select(FilterRule).where(
                            FilterRule.rule_json == rule
                        )
                    ).scalar_one_or_none()

                    if existing:
                        # Update metrics
                        existing.confidence = rule['confidence']
                        existing.support = rule['support']
                        existing.lift = rule['lift']
                    else:
                        # Create new
                        filter_rule = FilterRule(
                            rule_name=rule['rule_name'],
                            rule_json=rule,
                            confidence=rule['confidence'],
                            support=rule['support'],
                            lift=rule['lift'],
                            is_active=True,
                        )
                        db.add(filter_rule)

                db.commit()

            logger.info(f"💾 Saved {len(filter_rules)} filter rules to database")

        except Exception as e:
            logger.error(f"Error saving filter rules: {e}")

    async def load_active_rules(self) -> List[Dict]:
        """Load active filter rules from database"""
        try:
            with SessionLocal() as db:
                rules = db.execute(
                    select(FilterRule).where(FilterRule.is_active == True)
                ).scalars().all()

                self.blacklist_rules = [rule.rule_json for rule in rules]

                logger.info(f"📥 Loaded {len(self.blacklist_rules)} active filter rules")

                return self.blacklist_rules

        except Exception as e:
            logger.error(f"Error loading filter rules: {e}")
            return []

    def matches_blacklist_rule(self, features: Dict) -> Tuple[bool, Optional[Dict]]:
        """
        Check if trade features match any blacklist rule

        Args:
            features: Dictionary of trade features

        Returns:
            Tuple of (matches, matched_rule)
        """
        if not self.blacklist_rules:
            return False, None

        # Discretize current features
        features_df = pd.DataFrame([features])
        binned = self._discretize_features(features_df)

        if binned.empty:
            return False, None

        # Check each rule
        for rule in self.blacklist_rules:
            conditions = rule.get('conditions', [])

            # Check if all conditions are met
            all_met = True
            for condition in conditions:
                if condition in binned.columns:
                    if not binned[condition].iloc[0]:
                        all_met = False
                        break
                else:
                    all_met = False
                    break

            if all_met:
                logger.info(f"⚠️ Trade matches blacklist rule: {rule['rule_name']}")
                return True, rule

        return False, None

    async def update_rule_effectiveness(self, rule: Dict, prevented_loss: bool):
        """
        Update filter rule effectiveness metrics

        Args:
            rule: The filter rule that was triggered
            prevented_loss: True if blocking this trade prevented a loss
        """
        try:
            with SessionLocal() as db:
                filter_rule = db.execute(
                    select(FilterRule).where(
                        FilterRule.rule_name == rule['rule_name']
                    )
                ).scalar_one_or_none()

                if filter_rule:
                    filter_rule.trades_prevented += 1
                    filter_rule.last_triggered_at = datetime.now()

                    if not prevented_loss:
                        # This was a good trade we blocked (false negative)
                        filter_rule.false_negatives += 1

                    # Deactivate rule if too many false negatives
                    if filter_rule.false_negatives > 10:
                        filter_rule.is_active = False
                        logger.warning(f"⚠️ Deactivating rule {rule['rule_name']} due to false negatives")

                    db.commit()

        except Exception as e:
            logger.error(f"Error updating rule effectiveness: {e}")


# Singleton instance
anomaly_detector = AnomalyDetector()
