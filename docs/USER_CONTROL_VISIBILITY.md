# User Control & Visibility System

**Comprehensive User Control and Real-Time Monitoring for Trading Bot**

Version: 1.0.0
Date: January 2026
Author: Vector Protocol Team

---

## Table of Contents

1. [Overview](#overview)
2. [Backend Features (15 Optimizations)](#backend-features-15-optimizations)
3. [Frontend Recommendations (15 Optimizations)](#frontend-recommendations-15-optimizations)
4. [API Reference](#api-reference)
5. [Usage Examples](#usage-examples)
6. [Integration Guide](#integration-guide)

---

## Overview

The **User Control & Visibility System** is a comprehensive suite of 30 optimizations designed to give users complete control and visibility over their trading bot. This system provides real-time monitoring, advanced analytics, emergency controls, and customizable settings.

### System Components

- **11 Backend Modules**: Core functionality for control and monitoring
- **60+ API Endpoints**: RESTful APIs for all features
- **WebSocket Streaming**: Real-time updates (1-second intervals)
- **Multi-Channel Notifications**: Telegram, WebSocket, Email, Webhook
- **Audit Logging**: Complete action history for compliance
- **Rules Engine**: Customizable trading rules and constraints

---

## Backend Features (15 Optimizations)

### 1. Real-Time Snapshot Stream

**Module**: `backend/modules/control/snapshot_stream.py`

Provides 1-second updates of capital, positions, and bot status via WebSocket.

**Features:**
- Capital state (wallet, margin, P&L)
- Open positions (real-time prices, P&L)
- Bot status (running, paused, last action)
- Market data (optional, for watched symbols)
- Configurable update interval (0.1s - 60s)
- Historical snapshots (last 60 snapshots = 1 minute)

**API Endpoints:**
```
POST   /api/control/snapshot/start
POST   /api/control/snapshot/stop
GET    /api/control/snapshot/current
GET    /api/control/snapshot/history
PUT    /api/control/snapshot/config
```

**Example:**
```bash
# Start real-time streaming
curl -X POST "http://localhost:8000/api/control/snapshot/start"

# Get current snapshot
curl "http://localhost:8000/api/control/snapshot/current"

# Configure modules and interval
curl -X PUT "http://localhost:8000/api/control/snapshot/config?capital=true&positions=true&market_data=true&update_interval=2.0"
```

---

### 2. Advanced Notification Engine

**Module**: `backend/modules/control/notification_engine.py`

Configurable multi-channel notifications with triggers and filters.

**Features:**
- Multi-channel delivery (Telegram, WebSocket, Email, Webhook)
- 13 notification types (trade events, margin warnings, alerts, etc.)
- Priority-based routing (LOW, MEDIUM, HIGH, CRITICAL)
- Configurable triggers and filters
- Rate limiting per rule (cooldown periods)
- Notification history

**Notification Types:**
- `TRADE_OPENED`, `TRADE_CLOSED`
- `POSITION_PROFIT`, `POSITION_LOSS`
- `MARGIN_WARNING`, `MARGIN_CRITICAL`
- `BOT_STARTED`, `BOT_STOPPED`, `BOT_ERROR`
- `CAPITAL_MILESTONE`, `DRAWDOWN_ALERT`
- `PRICE_ALERT`, `CUSTOM_ALERT`

**API Endpoints:**
```
GET    /api/control/notifications/rules
GET    /api/control/notifications/history
```

**Example:**
```python
from modules.control import notification_engine, NotificationType, NotificationPriority

# Send notification
await notification_engine.send_notification(
    notification_type=NotificationType.TRADE_OPENED,
    title="🟢 Trade Opened",
    message="BTCUSDT LONG opened at $43,500",
    priority=NotificationPriority.MEDIUM,
    data={'symbol': 'BTCUSDT', 'side': 'LONG', 'price': 43500}
)
```

---

### 3. Manual Control API

**Module**: `backend/modules/control/manual_controls.py`

Manual override capabilities for bot and positions.

**Features:**
- Pause/Resume bot
- Close positions manually
- Adjust leverage per symbol
- Modify stop loss/take profit
- Add to position
- Reduce position size
- Control action history

**API Endpoints:**
```
POST   /api/control/bot/pause
POST   /api/control/bot/resume
POST   /api/control/position/close
POST   /api/control/position/adjust-leverage
POST   /api/control/position/modify-stop-loss
POST   /api/control/position/modify-take-profit
GET    /api/control/manual/history
```

**Example:**
```bash
# Pause bot
curl -X POST "http://localhost:8000/api/control/bot/pause?reason=Market%20volatility"

# Close position
curl -X POST "http://localhost:8000/api/control/position/close?symbol=BTCUSDT&reason=Take%20profit"

# Adjust leverage
curl -X POST "http://localhost:8000/api/control/position/adjust-leverage?symbol=ETHUSDT&leverage=5"
```

---

### 4. Trade Journal System

**Module**: `backend/modules/control/trade_journal.py`

Comprehensive trade tracking with tags, notes, and export capabilities.

**Features:**
- Track all trades with detailed metadata
- Add tags and notes
- Search and filter (symbol, side, outcome, tags, date range)
- Export to CSV/JSON
- Performance statistics
- Trade outcome categories (WIN, LOSS, BREAKEVEN, ONGOING)

**API Endpoints:**
```
POST   /api/control/journal/add
GET    /api/control/journal/search
GET    /api/control/journal/statistics
GET    /api/control/journal/export/csv
```

**Example:**
```python
from modules.control import trade_journal

# Add trade entry
await trade_journal.add_entry(
    symbol='BTCUSDT',
    side='LONG',
    entry_price=43500,
    exit_price=44200,
    quantity=0.1,
    leverage=10,
    pnl=700,
    pnl_pct=16.1,
    tags=['breakout', 'strong-signal'],
    notes='Perfect entry on 4H breakout',
    strategy='trend_following'
)

# Search entries
results = await trade_journal.search_entries(
    symbol='BTCUSDT',
    outcome=TradeOutcome.WIN,
    tags=['breakout'],
    limit=50
)

# Get statistics
stats = await trade_journal.get_statistics()
# Returns: total_trades, wins, losses, win_rate, avg_win, avg_loss, etc.
```

---

### 5. Performance Analytics API

**Module**: `backend/modules/control/performance_analytics.py`

Advanced performance metrics: Sharpe, Sortino, Win Rate, Profit Factor, etc.

**Features:**
- **Sharpe Ratio**: Risk-adjusted returns
- **Sortino Ratio**: Downside-focused risk metric
- **Maximum Drawdown**: Peak-to-trough decline
- **Win Rate**: Percentage of winning trades
- **Profit Factor**: Gross profit / Gross loss
- **Expectancy**: Average expected profit per trade
- **Symbol Performance**: Breakdown by trading pair

**API Endpoints:**
```
GET    /api/control/analytics/complete
GET    /api/control/analytics/sharpe?period_days=30
GET    /api/control/analytics/sortino?period_days=30
GET    /api/control/analytics/drawdown
GET    /api/control/analytics/win-rate?period_days=30
GET    /api/control/analytics/profit-factor?period_days=30
```

**Example:**
```bash
# Get complete analytics
curl "http://localhost:8000/api/control/analytics/complete"

# Get Sharpe ratio (30 days)
curl "http://localhost:8000/api/control/analytics/sharpe?period_days=30"

# Get maximum drawdown
curl "http://localhost:8000/api/control/analytics/drawdown"
```

**Response Example:**
```json
{
  "sharpe_ratio": 1.85,
  "sortino_ratio": 2.34,
  "max_drawdown": {
    "max_drawdown_pct": 8.5,
    "max_drawdown_usd": 425.0,
    "current_drawdown_pct": 2.3
  },
  "win_rate": {
    "total_trades": 127,
    "wins": 83,
    "losses": 42,
    "win_rate_pct": 65.35
  },
  "profit_factor": 2.15,
  "expectancy": {
    "expectancy": 45.20,
    "avg_win": 120.50,
    "avg_loss": 75.30,
    "reward_risk_ratio": 1.60
  }
}
```

---

### 6. Custom Alert Engine

**Module**: `backend/modules/control/alert_engine.py`

Configurable alerts for price, profit, loss, margin, and portfolio metrics.

**Features:**
- 9 alert types (price, profit, loss, margin, portfolio, position size, drawdown, custom)
- Real-time monitoring (5-second intervals)
- Configurable thresholds and comparisons
- Cooldown periods to prevent spam
- Notify-once option
- Alert history

**Alert Types:**
- `PRICE_ABOVE`, `PRICE_BELOW`
- `PROFIT_TARGET`, `LOSS_LIMIT`
- `MARGIN_USAGE`
- `PORTFOLIO_VALUE`
- `POSITION_SIZE`
- `DRAWDOWN`
- `CUSTOM` (with custom condition function)

**API Endpoints:**
```
POST   /api/control/alerts/create
GET    /api/control/alerts/list?status=active
DELETE /api/control/alerts/{alert_id}
POST   /api/control/alerts/start-monitoring
POST   /api/control/alerts/stop-monitoring
```

**Example:**
```python
from modules.control import alert_engine
from modules.control.alert_engine import Alert, AlertType, AlertStatus

# Create price alert
alert = Alert(
    id="btc_price_above_50k",
    name="BTC Above $50K",
    alert_type=AlertType.PRICE_ABOVE,
    symbol="BTCUSDT",
    target_value=50000.0,
    comparison=">",
    notify_once=True,
    cooldown_seconds=3600
)

await alert_engine.create_alert(alert)

# Start monitoring
await alert_engine.start_monitoring()
```

---

### 7. Emergency Controls

**Module**: `backend/modules/control/emergency_controls.py`

Panic button, emergency stop, reduce-all positions, circuit breakers.

**Features:**
- **Panic Close All**: Close all positions immediately (market orders)
- **Emergency Stop**: Stop bot + cancel all orders
- **Reduce All Positions**: Reduce all positions by percentage (default 50%)
- **Cancel All Orders**: Cancel all pending orders
- **Circuit Breaker**: Automatic emergency stop on loss threshold
- Emergency action history

**API Endpoints:**
```
POST   /api/control/emergency/panic-close-all?reason=Panic%20button
POST   /api/control/emergency/stop?reason=Emergency%20stop
POST   /api/control/emergency/reduce-all?reduce_pct=50.0
POST   /api/control/emergency/cancel-all-orders
GET    /api/control/emergency/circuit-breaker/status
POST   /api/control/emergency/circuit-breaker/reset
```

**Example:**
```bash
# PANIC: Close all positions immediately
curl -X POST "http://localhost:8000/api/control/emergency/panic-close-all?reason=Market%20crash"

# Reduce all positions by 70%
curl -X POST "http://localhost:8000/api/control/emergency/reduce-all?reduce_pct=70.0"

# Enable circuit breaker (10% daily loss)
python -c "
from modules.control import emergency_controller
emergency_controller.enable_circuit_breaker(loss_pct=10.0)
"
```

---

### 8. Audit Log System

**Module**: `backend/modules/control/audit_logger.py`

Centralized logging of all critical actions for compliance and debugging.

**Features:**
- 30+ audit action types
- 3 severity levels (INFO, WARNING, CRITICAL)
- Structured logging with metadata
- Search and filter capabilities
- Export to JSON
- 90-day retention (configurable)
- Statistics and reporting

**Audit Action Types:**
- Trading: TRADE_OPENED, TRADE_CLOSED, ORDER_PLACED, etc.
- Position: POSITION_MODIFIED, LEVERAGE_CHANGED, etc.
- Bot: BOT_STARTED, BOT_STOPPED, BOT_PAUSED, etc.
- Emergency: PANIC_CLOSE, EMERGENCY_STOP, CIRCUIT_BREAKER
- Settings: SETTINGS_CHANGED, RULE_CREATED, etc.

**API Endpoints:**
```
GET    /api/control/audit/search
GET    /api/control/audit/recent?limit=100
GET    /api/control/audit/statistics
GET    /api/control/audit/export
```

**Example:**
```python
from modules.control import audit_logger
from modules.control.audit_logger import AuditAction, AuditLevel

# Log action
await audit_logger.log(
    action=AuditAction.TRADE_OPENED,
    message="Opened LONG position on BTCUSDT at $43,500",
    level=AuditLevel.INFO,
    user="bot",
    metadata={
        'symbol': 'BTCUSDT',
        'side': 'LONG',
        'price': 43500,
        'quantity': 0.1,
        'leverage': 10
    }
)

# Search audit log
results = await audit_logger.search(
    action=AuditAction.EMERGENCY_STOP,
    level=AuditLevel.CRITICAL,
    search_text="circuit breaker",
    limit=50
)
```

---

### 9. Custom Rules Engine

**Module**: `backend/modules/control/rules_engine.py`

Define and enforce trading rules based on time, limits, and conditions.

**Features:**
- **Temporal Rules**: Trading hours, days of week, time ranges
- **Limit Rules**: Max trades/day, max leverage, max loss/day, position size
- **Condition Rules**: Custom rule functions
- Rule violation tracking
- Enforcement modes (block, warn, notify)
- Daily statistics reset

**Default Rules:**
- No weekend trading (Mon-Fri only)
- Max 20 trades per day
- Max 10% daily loss
- Max 20x leverage

**API Endpoints:**
```
GET    /api/control/rules/check
GET    /api/control/rules/list?status=active
GET    /api/control/rules/violations?limit=100
GET    /api/control/rules/daily-stats
```

**Example:**
```python
from modules.control import rules_engine
from modules.control.rules_engine import TradingRule, RuleType

# Create custom rule
rule = TradingRule(
    id="no_trading_9am_to_10am",
    name="No Trading 9-10 AM",
    rule_type=RuleType.TEMPORAL,
    description="Avoid high volatility during market open",
    start_time=time(10, 0),  # Trading starts at 10:00 AM
    end_time=time(23, 59),   # Trading ends at 11:59 PM
    enforce=True
)

rules_engine.add_rule(rule)

# Check if trading is allowed
result = await rules_engine.check_can_trade()
if result['allowed']:
    print("Trading is allowed")
else:
    print(f"Trading blocked: {result['violations']}")
```

---

### 10. Quick Actions API

**Module**: `backend/modules/control/quick_actions.py`

One-click actions for common trading operations.

**Features:**
- Close All Profitable (min profit threshold)
- Close All Losing (max loss threshold)
- Reduce Risk Mode (reduce positions + lower leverage)
- Emergency Mode (stop bot + close losing positions)
- Scale Out Winners (partial profit taking)
- Action history

**API Endpoints:**
```
POST   /api/control/quick-actions/close-profitable?min_profit_pct=1.0
POST   /api/control/quick-actions/close-losing?max_loss_pct=-2.0
POST   /api/control/quick-actions/reduce-risk-mode
POST   /api/control/quick-actions/emergency-mode
POST   /api/control/quick-actions/scale-out-winners?profit_threshold_pct=3.0&scale_pct=50.0
GET    /api/control/quick-actions/history
```

**Example:**
```bash
# Close all profitable positions (>1% profit)
curl -X POST "http://localhost:8000/api/control/quick-actions/close-profitable?min_profit_pct=1.0"

# Scale out 50% of winners (>3% profit)
curl -X POST "http://localhost:8000/api/control/quick-actions/scale-out-winners?profit_threshold_pct=3.0&scale_pct=50.0"

# Activate reduce risk mode
curl -X POST "http://localhost:8000/api/control/quick-actions/reduce-risk-mode"
```

---

### 11. User Settings & Preferences

**Module**: `backend/modules/control/user_settings.py`

Persistent configuration and user profiles.

**Features:**
- 6 settings categories (trading, notifications, display, risk, alerts, advanced)
- Multiple profiles/presets (Conservative, Moderate, Aggressive)
- Settings validation
- Import/Export to JSON
- Per-category updates

**Settings Categories:**
- **Trading**: Leverage, risk %, order timeout, trailing stop
- **Notifications**: Telegram, email, WebSocket, thresholds
- **Display**: Theme, language, currency, decimal places
- **Risk**: Max portfolio risk, margin limits, circuit breaker
- **Alerts**: Price alerts, profit alerts, check interval
- **Advanced**: Auto-sync, log level, cache TTL

**API Endpoints:**
```
GET    /api/control/settings/all
GET    /api/control/settings/{category}
PUT    /api/control/settings/{category}
POST   /api/control/settings/reset
GET    /api/control/settings/profiles
POST   /api/control/settings/profiles/{profile_id}/activate
GET    /api/control/settings/export
POST   /api/control/settings/import
```

**Example:**
```bash
# Get all settings
curl "http://localhost:8000/api/control/settings/all"

# Update trading settings
curl -X PUT "http://localhost:8000/api/control/settings/trading" \
  -H 'Content-Type: application/json' \
  -d '{
    "settings": {
      "default_leverage": 15,
      "max_leverage": 20,
      "default_risk_pct": 2.5
    }
  }'

# Activate conservative profile
curl -X POST "http://localhost:8000/api/control/settings/profiles/conservative/activate"

# Export settings
curl "http://localhost:8000/api/control/settings/export" > settings_backup.json
```

---

## Frontend Recommendations (15 Optimizations)

The following are recommended frontend improvements to enhance user experience on both desktop and mobile:

### 12. Mobile-First Responsive Dashboard
- **3-column → 2-column → 1-column layout**
- Responsive grid with CSS Grid/Flexbox
- Bottom navigation for mobile (5 main tabs)
- Touch-friendly UI elements (min 44x44px)

### 13. Progressive Web App (PWA)
- Service worker for offline support
- App manifest for "Add to Home Screen"
- Caching strategy for API responses
- Background sync for offline actions

### 14. Interactive Touch-Optimized Charts
- TradingView Lightweight Charts or Recharts
- Pinch-to-zoom, pan gestures
- Touch-optimized crosshair
- Multi-timeframe switching

### 15. Modular Card-Based Layout
- Drag-and-drop dashboard customization
- Resizable cards
- Layout presets (trading, monitoring, analytics)
- Persistent layout state

### 16. Smart Table Component (Virtualized)
- React Virtual or Tanstack Virtual
- Infinite scroll for large datasets
- Sortable, filterable columns
- Export to CSV

### 17. Dark/Light Theme Toggle + Custom
- 3 theme options: Dark, Light, OLED
- Auto theme switching (time-based)
- Custom color scheme builder
- Theme persistence

### 18. Skeleton Loading States
- Progressive loading with skeleton screens
- Shimmer effect animation
- Better perceived performance

### 19. Pull-to-Refresh (Mobile)
- Native-like pull gesture for data refresh
- Works on positions, trades, analytics pages

### 20. Smart Search & Command Palette
- CMD+K or CTRL+K to open
- Fuzzy search across all features
- Recent searches
- Quick actions

### 21. Position Detail Modal
- Fullscreen modal on mobile
- Swipe gestures to close
- Quick actions (modify SL/TP, close, add/reduce)
- Real-time P&L updates

### 22. Quick Stats Cards
- Glanceable metrics (total P&L, win rate, positions)
- Sparklines for trends
- Click to drill down

### 23. Toast Notification System
- 4 types: success, error, warning, info
- Auto-dismiss with configurable duration
- Swipe to dismiss (mobile)
- Stack management

### 24. Offline Mode & Data Persistence
- Service worker caching
- IndexedDB for local storage
- Queue offline actions
- Sync when online

### 25. Accessibility (A11y) Improvements
- WCAG AAA compliance
- Keyboard navigation
- Screen reader support
- Focus management

### 26. Performance Optimizations
- Code splitting with React.lazy
- Bundle size analysis with webpack-bundle-analyzer
- Image optimization (WebP, lazy loading)
- Memoization for expensive components

---

## API Reference

### Base URL
```
http://localhost:8000
```

### Authentication
If `API_AUTH_ENABLED=true` in settings:
```bash
# Header-based
curl -H "X-API-Key: your-api-key" ...

# Query parameter
curl "http://localhost:8000/api/control/...?api_key=your-api-key"
```

### Response Format
```json
{
  "status": "success",
  "data": { ... }
}
```

### Error Format
```json
{
  "detail": "Error message"
}
```

### Endpoint Summary

**Snapshot Stream** (5 endpoints)
- Start/stop streaming, get current, history, configure

**Manual Controls** (7 endpoints)
- Pause/resume bot, close/modify positions, control history

**Trade Journal** (4 endpoints)
- Add entry, search, statistics, export

**Performance Analytics** (6 endpoints)
- Complete analytics, Sharpe, Sortino, drawdown, win rate, profit factor

**Alerts** (5 endpoints)
- Create, list, delete, start/stop monitoring

**Emergency** (6 endpoints)
- Panic close, emergency stop, reduce all, cancel orders, circuit breaker

**Audit Log** (4 endpoints)
- Search, recent, statistics, export

**Rules** (4 endpoints)
- Check, list, violations, daily stats

**Quick Actions** (6 endpoints)
- Close profitable/losing, reduce risk, emergency, scale out, history

**User Settings** (9 endpoints)
- Get/set settings, profiles, export/import

**Notifications** (2 endpoints)
- Rules, history

**Total: 60+ endpoints**

---

## Usage Examples

### Complete Workflow Example

```python
import asyncio
from modules.control import *

async def complete_workflow():
    # 1. Start real-time monitoring
    await snapshot_stream_manager.start_stream()

    # 2. Create price alert
    alert = Alert(
        id="btc_50k",
        name="BTC Above $50K",
        alert_type=AlertType.PRICE_ABOVE,
        symbol="BTCUSDT",
        target_value=50000.0
    )
    await alert_engine.create_alert(alert)
    await alert_engine.start_monitoring()

    # 3. Check trading rules
    result = await rules_engine.check_can_trade()
    if not result['allowed']:
        print(f"Trading blocked: {result['violations']}")
        return

    # 4. Get analytics
    analytics = await performance_analytics.get_complete_analytics()
    print(f"Sharpe Ratio: {analytics['sharpe_ratio']}")
    print(f"Win Rate: {analytics['win_rate']['win_rate_pct']}%")

    # 5. If losing >5%, activate reduce risk mode
    current_dd = analytics['max_drawdown']['current_drawdown_pct']
    if current_dd > 5.0:
        result = await quick_actions_manager.reduce_risk_mode()
        print(f"Risk reduction activated: {result}")

    # 6. Log action
    await audit_logger.log(
        action=AuditAction.BOT_STARTED,
        message="Bot started with complete monitoring",
        level=AuditLevel.INFO,
        user="system"
    )

asyncio.run(complete_workflow())
```

### Telegram Bot Integration

```python
from modules.control import notification_engine, NotificationType, NotificationPriority

# Configure Telegram notifications
notification_engine.add_rule(NotificationRule(
    id="telegram_all_trades",
    name="Telegram: All Trades",
    notification_type=NotificationType.TRADE_OPENED,
    channels=[NotificationChannel.TELEGRAM],
    priority=NotificationPriority.MEDIUM
))

# Send custom notification
await notification_engine.send_notification(
    notification_type=NotificationType.CUSTOM_ALERT,
    title="🎯 Trading Milestone",
    message="Reached 100 trades with 65% win rate!",
    priority=NotificationPriority.HIGH
)
```

---

## Integration Guide

### Step 1: Start Snapshot Stream

```python
from modules.control import snapshot_stream_manager

# Start streaming
await snapshot_stream_manager.start_stream()

# Configure modules
snapshot_stream_manager.configure_modules({
    'capital': True,
    'positions': True,
    'bot_status': True,
    'market_data': False  # Disable to reduce bandwidth
})

# Set update interval
snapshot_stream_manager.set_update_interval(2.0)  # 2 seconds
```

### Step 2: Enable Alerts

```python
from modules.control import alert_engine

# Start alert monitoring
await alert_engine.start_monitoring()

# Create alerts
alerts = [
    Alert(id="margin_high", name="Margin >75%", alert_type=AlertType.MARGIN_USAGE, target_value=75.0),
    Alert(id="profit_5pct", name="Profit >5%", alert_type=AlertType.PROFIT_TARGET, target_value=5.0),
    Alert(id="loss_3pct", name="Loss >3%", alert_type=AlertType.LOSS_LIMIT, target_value=3.0)
]

for alert in alerts:
    await alert_engine.create_alert(alert)
```

### Step 3: Configure Notifications

```python
from modules.control import notification_engine

# Notifications are configured by default
# Customize rules as needed
notification_engine.update_rule(
    "trade_opened_telegram",
    channels=[NotificationChannel.TELEGRAM, NotificationChannel.WEBSOCKET]
)
```

### Step 4: Set Trading Rules

```python
from modules.control import rules_engine

# Default rules are already configured
# Add custom rules as needed
custom_rule = TradingRule(
    id="lunch_break",
    name="No Trading 12-1 PM",
    rule_type=RuleType.TEMPORAL,
    start_time=time(13, 0),  # Resume at 1 PM
    end_time=time(23, 59),
    enforce=True
)

rules_engine.add_rule(custom_rule)
```

### Step 5: Monitor and Control

```python
# Check bot status
snapshot = await snapshot_stream_manager.get_current_snapshot()
print(f"Bot Status: {snapshot['data']['bot_status']}")
print(f"Capital: ${snapshot['data']['capital']['wallet_balance']}")

# Pause bot if needed
from modules.control import manual_control_manager

if high_volatility:
    await manual_control_manager.pause_bot(reason="High volatility")

# Resume later
await manual_control_manager.resume_bot()
```

---

## Best Practices

### 1. Always Check Rules Before Trading
```python
result = await rules_engine.check_can_trade()
if not result['allowed']:
    print(f"Trading blocked: {result['enforced_violations']}")
    return
```

### 2. Use Audit Logging for All Critical Actions
```python
await audit_logger.log(
    action=AuditAction.POSITION_CLOSED,
    message=f"Closed {symbol} position",
    level=AuditLevel.INFO,
    metadata={'symbol': symbol, 'pnl': pnl}
)
```

### 3. Set Up Emergency Controls
```python
# Enable circuit breaker
emergency_controller.enable_circuit_breaker(loss_pct=10.0)

# Monitor drawdown
if current_drawdown > 8.0:
    await emergency_controller.emergency_stop("Drawdown exceeded 8%")
```

### 4. Track Performance with Journal
```python
# Add every trade to journal
await trade_journal.add_entry(
    symbol=symbol,
    side=side,
    entry_price=entry_price,
    exit_price=exit_price,
    quantity=quantity,
    leverage=leverage,
    pnl=pnl,
    pnl_pct=pnl_pct,
    tags=['strategy_name', 'market_condition'],
    notes="Trade rationale"
)
```

### 5. Use Profiles for Different Strategies
```python
# Activate conservative profile during volatile markets
await user_settings_manager.activate_profile("conservative")

# Activate aggressive profile during strong trends
await user_settings_manager.activate_profile("aggressive")
```

---

## Troubleshooting

### Snapshot Stream Not Updating
```python
# Check if stream is running
from modules.control import snapshot_stream_manager

print(f"Stream running: {snapshot_stream_manager.is_running}")

# Restart stream
await snapshot_stream_manager.stop_stream()
await snapshot_stream_manager.start_stream()
```

### Alerts Not Triggering
```python
from modules.control import alert_engine

# Check if monitoring is running
print(f"Monitoring: {alert_engine.is_monitoring}")

# Check alert status
alerts = await alert_engine.get_alerts(status=AlertStatus.ACTIVE)
print(f"Active alerts: {len(alerts)}")

# Restart monitoring
await alert_engine.stop_monitoring()
await alert_engine.start_monitoring()
```

### Rules Blocking Trades
```python
# Get rule violations
result = await rules_engine.check_can_trade()
print(f"Violations: {result['violations']}")

# Temporarily disable rule
rules_engine.update_rule(rule_id, status=RuleStatus.INACTIVE)
```

---

## Performance Considerations

- **Snapshot Stream**: 1-second updates can be CPU-intensive. Increase interval to 2-5s for production
- **Alert Engine**: Limit active alerts to <50 for optimal performance
- **Audit Log**: Automatically cleans up entries >90 days old
- **Trade Journal**: Maximum 10,000 entries (oldest automatically removed)

---

## Security Notes

- All control actions are logged in audit log
- Emergency controls require no confirmation (by design)
- API authentication recommended for production (`API_AUTH_ENABLED=true`)
- Telegram notifications should use secure bot tokens
- Export functions (settings, journal, audit log) contain sensitive data - handle carefully

---

## Future Enhancements

### Planned Features

1. **Position Heatmap Data API**: Structured data for visual heatmaps
2. **Backtest Simulator API**: What-if scenario testing
3. **Strategy A/B Testing**: Side-by-side strategy comparison
4. **Market Opportunity Scanner**: Real-time scanner with WebSocket

### Frontend Optimizations (To Be Implemented)

All 15 frontend recommendations (#12-#26) are documented above and ready for implementation. These include:
- Mobile-first responsive design
- PWA support
- Touch-optimized charts
- Modular layout
- Virtualized tables
- Theme system
- Performance optimizations
- Accessibility improvements

---

## Conclusion

The **User Control & Visibility System** provides comprehensive control and monitoring capabilities for the Vector Protocol trading bot. With 11 backend modules, 60+ API endpoints, and 15 recommended frontend optimizations, users have complete visibility and control over their automated trading operations.

For questions or support, please refer to the main documentation or contact the Vector Protocol team.

---

**Document Version**: 1.0.0
**Last Updated**: January 2026
**Status**: Production Ready (Backend Complete, Frontend Recommended)
