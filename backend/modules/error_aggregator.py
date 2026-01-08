"""
Error Aggregator - Phase 4
Tracks and aggregates errors in Redis for health monitoring
"""
import json
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import redis

from config.settings import get_settings
from utils.logger import setup_logger

logger = setup_logger("error_aggregator")
settings = get_settings()


class ErrorAggregator:
    """
    Aggregates and stores errors in Redis for health dashboard.

    Features:
    - Stores recent errors in Redis sorted set (last 1000)
    - Tracks hourly error counts per component
    - Provides error rate calculations
    - 7-day retention for error statistics
    """

    def __init__(self):
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=0,
                decode_responses=True
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Error aggregator initialized with Redis connection")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None

    async def track_error(
        self,
        component: str,
        level: str,
        message: str,
        traceback: Optional[str] = None
    ):
        """
        Store error in Redis sorted set.

        Args:
            component: Component name (e.g., 'api', 'order_executor', 'bot')
            level: Log level (ERROR, CRITICAL, WARNING)
            message: Error message
            traceback: Optional traceback string
        """
        if not self.redis_client:
            return

        try:
            timestamp = time.time()
            error_data = {
                "timestamp": timestamp,
                "component": component,
                "level": level,
                "message": message,
                "traceback": traceback
            }

            # Store in Redis sorted set (score = timestamp for time-based queries)
            self.redis_client.zadd(
                "errors:recent",
                {json.dumps(error_data): timestamp}
            )

            # Keep only last 1000 errors
            self.redis_client.zremrangebyrank("errors:recent", 0, -1001)

            # Increment hourly counter for component
            hour_key = f"errors:count:{component}:{datetime.utcnow().strftime('%Y%m%d%H')}"
            self.redis_client.incr(hour_key)
            self.redis_client.expire(hour_key, 86400 * 7)  # 7 days retention

            logger.debug(f"Tracked error for {component}: {message[:50]}")

        except Exception as e:
            logger.error(f"Failed to track error in Redis: {e}")

    async def get_recent_errors(
        self,
        limit: int = 50,
        component: Optional[str] = None,
        level: Optional[str] = None
    ) -> List[Dict]:
        """
        Fetch recent errors from Redis.

        Args:
            limit: Maximum number of errors to return
            component: Filter by component name
            level: Filter by log level

        Returns:
            List of error dicts sorted by timestamp (newest first)
        """
        if not self.redis_client:
            return []

        try:
            # Get errors from sorted set (newest first)
            errors_raw = self.redis_client.zrevrange("errors:recent", 0, limit - 1)

            result = []
            for error_json in errors_raw:
                error = json.loads(error_json)

                # Apply filters
                if component and error.get('component') != component:
                    continue
                if level and error.get('level') != level:
                    continue

                result.append(error)

                # Stop if we have enough results
                if len(result) >= limit:
                    break

            logger.debug(f"Retrieved {len(result)} recent errors")
            return result

        except Exception as e:
            logger.error(f"Failed to get recent errors: {e}")
            return []

    async def get_error_rate(
        self,
        component: Optional[str] = None,
        hours: int = 24
    ) -> Dict:
        """
        Calculate error rate per hour.

        Args:
            component: Filter by component name (None = all components)
            hours: Number of hours to analyze

        Returns:
            Dict with hourly counts, total, and average
        """
        if not self.redis_client:
            return {"hourly": [], "total": 0, "average_per_hour": 0.0}

        try:
            now = datetime.utcnow()
            hourly_counts = []

            for i in range(hours):
                hour = (now - timedelta(hours=i)).strftime('%Y%m%d%H')

                if component:
                    # Specific component
                    key = f"errors:count:{component}:{hour}"
                    count = int(self.redis_client.get(key) or 0)
                else:
                    # All components
                    pattern = f"errors:count:*:{hour}"
                    keys = self.redis_client.keys(pattern)
                    count = sum(int(self.redis_client.get(k) or 0) for k in keys)

                hourly_counts.append({
                    "hour": hour,
                    "count": count
                })

            total = sum(h['count'] for h in hourly_counts)
            average = total / hours if hours > 0 else 0.0

            return {
                "hourly": hourly_counts,
                "total": total,
                "average_per_hour": round(average, 2)
            }

        except Exception as e:
            logger.error(f"Failed to get error rate: {e}")
            return {"hourly": [], "total": 0, "average_per_hour": 0.0}

    async def get_error_summary(self) -> Dict:
        """
        Get error summary statistics.

        Returns:
            Dict with error counts by component and level
        """
        if not self.redis_client:
            return {"by_component": {}, "by_level": {}, "total": 0}

        try:
            errors = await self.get_recent_errors(limit=1000)

            by_component = {}
            by_level = {}

            for error in errors:
                comp = error.get('component', 'unknown')
                lvl = error.get('level', 'UNKNOWN')

                by_component[comp] = by_component.get(comp, 0) + 1
                by_level[lvl] = by_level.get(lvl, 0) + 1

            return {
                "by_component": by_component,
                "by_level": by_level,
                "total": len(errors)
            }

        except Exception as e:
            logger.error(f"Failed to get error summary: {e}")
            return {"by_component": {}, "by_level": {}, "total": 0}


# Singleton instance
error_aggregator = ErrorAggregator()
