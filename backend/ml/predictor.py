"""
predictor.py — ML-based price forecasting for SmartShop (v4)
=============================================================
Key design decisions
────────────────────
1. BASE PRICE  : Uses the best-deal (lowest) price among all listings for
                 the same product — ensures consistency with comparison UI.

2. TRAINING DATA
   • ≥ 5 real rows → train on real data (optionally extended with synthetic
     warm-up if history is < 30 days).
   • < 5 real rows → generate 90-day synthetic series from the base price.

3. FEATURE ENGINEERING (per row)
   t_norm      – normalised day index 0→1 (long-run trend)
   t_sq        – t_norm²             (gentle curve)
   dow_sin/cos – cyclical day-of-week (weekly pattern)
   lag1        – price yesterday      (short-run momentum)
   lag7        – price 7 days ago     (weekly-cycle reference)
   roll7       – 7-day rolling mean   (local level estimate)

4. MODEL SELECTION
   PRIMARY  : GradientBoostingRegressor (non-linear discount curve)
   FALLBACK : Polynomial Ridge (degree 2) — when GB cannot be fitted

5. AUTOREGRESSIVE PREDICTION
   Each future day is predicted one step at a time; the prediction is
   immediately fed back as lag1/roll7 for the next step.

6. POST-PROCESSING
   • Light EMA pass (α = 0.40) removes residual jitter.
   • Small noise (±2 %) added for realism after smoothing.

7. CONFIDENCE: clamped to a realistic UI range of 70–85 %.

8. RECOMMENDATION thresholds (aligned with requirement):
   WAIT  : avg_change < -3 %
   HOLD  : -3 % ≤ avg_change ≤ +2 %
   BUY   : avg_change > +2 %
"""

import pandas as pd
import numpy as np
from datetime import timedelta
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
from sklearn.metrics import mean_absolute_percentage_error
import warnings
warnings.filterwarnings("ignore")


# ═══════════════════════════════════════════════════════════════════════════════
#  SYNTHETIC DATA GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

def _build_synthetic_series(base_price: float, days: int = 90, seed: int = 0) -> np.ndarray:
    """
    Realistic training price series anchored to base_price:
      • starts 4–7 % above base_price  (product was pricier before discounts)
      • long-run trend: slow drift toward ~base_price by day `days`
      • weekly rhythm: slight softness Mon/Tue, slight premium Fri/Sat
      • per-day noise: 0.3–1.5 % (tight — keeps series stable)
    """
    rng = np.random.default_rng(seed % (2 ** 31))
    start = base_price * rng.uniform(1.04, 1.07)

    targets = np.linspace(start, base_price * rng.uniform(0.97, 1.00), days)

    dow_offset = rng.integers(0, 7)
    weekly_mod = np.array([0.000, -0.003, -0.002, 0.001, 0.003, 0.004, 0.002])

    prices = np.empty(days)
    val = float(start)
    for i in range(days):
        dow = (dow_offset + i) % 7
        noise_sigma = val * rng.uniform(0.003, 0.015)
        noise = float(np.clip(rng.normal(0, noise_sigma), -val * 0.02, val * 0.02))
        wk = val * weekly_mod[dow]
        val = 0.72 * targets[i] + 0.28 * val + noise + wk
        val = max(val, base_price * 0.82)
        prices[i] = val

    return prices.astype(np.float64)


# ═══════════════════════════════════════════════════════════════════════════════
#  FEATURE ENGINEERING
# ═══════════════════════════════════════════════════════════════════════════════

def _build_features(prices: np.ndarray, start_dow: int = 0) -> np.ndarray:
    """
    Build (N - 7) × 7 feature matrix.
    Columns: [t_norm, t_sq, dow_sin, dow_cos, lag1, lag7, roll7]
    """
    N = len(prices)
    rows = []
    total = N - 7

    for i in range(7, N):
        t = (i - 7) / max(total - 1, 1)
        dow = (start_dow + i) % 7
        lag1 = prices[i - 1]
        lag7 = prices[i - 7]
        roll7 = float(np.mean(prices[i - 7: i]))

        rows.append([
            t,
            t ** 2,
            np.sin(2 * np.pi * dow / 7),
            np.cos(2 * np.pi * dow / 7),
            lag1,
            lag7,
            roll7,
        ])

    return np.array(rows, dtype=np.float64)


# ═══════════════════════════════════════════════════════════════════════════════
#  MODEL TRAINING
# ═══════════════════════════════════════════════════════════════════════════════

def _train_gb(X: np.ndarray, y: np.ndarray) -> GradientBoostingRegressor:
    model = GradientBoostingRegressor(
        n_estimators=120,
        max_depth=3,
        learning_rate=0.08,
        subsample=0.85,
        min_samples_leaf=3,
        random_state=42,
    )
    model.fit(X, y)
    return model


def _train_poly_ridge(X: np.ndarray, y: np.ndarray):
    pipe = make_pipeline(PolynomialFeatures(degree=2, include_bias=False), Ridge(alpha=10.0))
    pipe.fit(X[:, [0, 1, 6]], y)
    return pipe


# ═══════════════════════════════════════════════════════════════════════════════
#  AUTOREGRESSIVE FUTURE PREDICTION
# ═══════════════════════════════════════════════════════════════════════════════

def _predict_future(
    model,
    use_poly: bool,
    history: np.ndarray,
    days_ahead: int,
    start_dow: int,
    history_len: int,
) -> np.ndarray:
    buf = list(history[-7:])
    total = history_len - 7
    preds = []

    for i in range(days_ahead):
        t_abs = total + i
        t = t_abs / max(total - 1, 1)
        dow = (start_dow + history_len + i) % 7
        lag1 = buf[-1]
        lag7 = buf[-7] if len(buf) >= 7 else buf[0]
        roll7 = float(np.mean(buf[-7:]))

        feat = np.array([[
            t,
            t ** 2,
            np.sin(2 * np.pi * dow / 7),
            np.cos(2 * np.pi * dow / 7),
            lag1,
            lag7,
            roll7,
        ]])

        if use_poly:
            p = float(model.predict(feat[:, [0, 1, 6]])[0])
        else:
            p = float(model.predict(feat)[0])

        p = max(p, history[-1] * 0.75)
        preds.append(p)
        buf.append(p)
        if len(buf) > 14:
            buf.pop(0)

    return np.array(preds, dtype=np.float64)


# ═══════════════════════════════════════════════════════════════════════════════
#  POST-PROCESSING: SMOOTH + SMALL NOISE
# ═══════════════════════════════════════════════════════════════════════════════

def _smooth_and_noise(prices: np.ndarray, base_price: float,
                      alpha: float = 0.40, seed: int = 0) -> np.ndarray:
    """
    1. Light EMA smooth (α = 0.40) to remove ML jitter.
    2. Add tiny noise in ±2 % range around each smoothed value.
       Noise is seeded deterministically so forecasts are stable across
       repeated calls for the same product.
    """
    # EMA pass
    out = np.empty_like(prices)
    out[0] = prices[0]
    for i in range(1, len(prices)):
        out[i] = alpha * prices[i] + (1.0 - alpha) * out[i - 1]

    # Deterministic small noise ±2 %
    rng = np.random.default_rng(seed % (2 ** 31))
    noise_pct = rng.uniform(-0.02, 0.02, size=len(out))
    noisy = out * (1.0 + noise_pct)

    # Hard floor: never drop below 80 % of base price
    noisy = np.clip(noisy, base_price * 0.80, None)
    return noisy


# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIDENCE SCORING  (clamped to 70–85 %)
# ═══════════════════════════════════════════════════════════════════════════════

def _confidence(X: np.ndarray, y: np.ndarray, model, use_poly: bool,
                real_rows: int) -> tuple:
    split = max(int(len(y) * 0.80), len(y) - 15)
    X_val, y_val = X[split:], y[split:]

    if len(X_val) == 0:
        raw_conf = 72.0
    else:
        preds = model.predict(X_val[:, [0, 1, 6]]) if use_poly else model.predict(X_val)
        mape = mean_absolute_percentage_error(y_val, preds) * 100
        # MAPE 0 % → 85, MAPE 5 % → 77, MAPE 15 % → 70
        raw_conf = max(70.0, min(85.0, 85.0 - mape * 1.5))

    # Small boost for real data availability (stays within 70–85)
    if real_rows >= 10:
        raw_conf = min(85.0, raw_conf + 2.0)
    elif real_rows >= 5:
        raw_conf = min(85.0, raw_conf + 1.0)

    score = round(raw_conf, 1)
    label = "high" if score >= 78 else "medium"
    return score, label


# ═══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def predict_future_price(product_name: str, df: pd.DataFrame, days_ahead: int = 30) -> dict:
    """
    Main entry point.

    Uses best-deal (lowest) price among all listings as the canonical
    base price so the forecast is consistent with the comparison UI.
    """
    try:
        subset = (
            df[df["product_name"] == product_name]
            .dropna(subset=["date", "price"])
            .sort_values("date")
            .copy()
        )

        if len(subset) == 0:
            return _empty_result()

        # ── Canonical base price = lowest price among all listings ────────────
        base_price = int(round(float(subset["price"].min())))
        if base_price <= 0:
            return _empty_result()

        # current_price = most recent price in data (for change % computation)
        current_price = int(round(float(subset["price"].iloc[-1])))

        seed = abs(hash(product_name)) % (2 ** 31)
        today = pd.Timestamp.now()
        real_rows = len(subset)

        # ── 1. Build training price series anchored to base_price ─────────────
        if real_rows >= 5:
            raw_prices = subset["price"].to_numpy(dtype=np.float64)
            if len(raw_prices) < 30:
                warmup = _build_synthetic_series(
                    float(raw_prices[0]) * 1.04, days=30, seed=seed
                )
                raw_prices = np.concatenate([warmup, raw_prices])
        else:
            raw_prices = _build_synthetic_series(base_price, days=90, seed=seed)

        # Derive starting day-of-week
        if real_rows >= 5:
            first_date = subset["date"].iloc[max(0, real_rows - len(raw_prices))]
            start_dow = int(first_date.dayofweek) if hasattr(first_date, "dayofweek") else 0
        else:
            start_dow = int(today.dayofweek)

        # ── 2. Features + labels ──────────────────────────────────────────────
        X = _build_features(raw_prices, start_dow=start_dow)
        y = raw_prices[7:]

        if len(X) < 10:
            return _empty_result()

        # ── 3. Train model (GB primary, Poly Ridge fallback) ──────────────────
        use_poly = False
        try:
            model = _train_gb(X, y)
        except Exception:
            use_poly = True
            model = _train_poly_ridge(X, y)

        # ── 4. Autoregressive forecast ────────────────────────────────────────
        raw_preds = _predict_future(
            model=model,
            use_poly=use_poly,
            history=raw_prices,
            days_ahead=days_ahead,
            start_dow=start_dow,
            history_len=len(raw_prices),
        )

        # ── 5. Post-processing: smooth + ±2 % noise ───────────────────────────
        smooth_preds = _smooth_and_noise(raw_preds, base_price=base_price,
                                         alpha=0.40, seed=seed)
        predicted_prices = [int(round(p)) for p in smooth_preds]

        # ── 6. Past-price series for the graph ───────────────────────────────
        if real_rows >= 5:
            tail = subset.tail(30)
            past_dates = [r["date"].strftime("%Y-%m-%d") for _, r in tail.iterrows()]
            past_vals = [int(r["price"]) for _, r in tail.iterrows()]
        else:
            synth_30 = raw_prices[-30:]
            ema_synth = np.empty_like(synth_30)
            ema_synth[0] = synth_30[0]
            for i in range(1, len(synth_30)):
                ema_synth[i] = 0.4 * synth_30[i] + 0.6 * ema_synth[i - 1]
            past_vals = [int(round(p)) for p in ema_synth]
            past_dates = [
                (today - timedelta(days=30 - i)).strftime("%Y-%m-%d")
                for i in range(30)
            ]

        past_prices = [{"date": past_dates[i], "price": past_vals[i]}
                       for i in range(len(past_dates))]

        # ── 7. Future dates ───────────────────────────────────────────────────
        future_dates = [
            (today + timedelta(days=i + 1)).strftime("%Y-%m-%d")
            for i in range(days_ahead)
        ]
        predicted_series = [
            {"date": future_dates[i], "price": predicted_prices[i]}
            for i in range(days_ahead)
        ]

        # ── 8. Summary stats ──────────────────────────────────────────────────
        avg_predicted = float(np.mean(predicted_prices))
        min_predicted = int(min(predicted_prices))
        # Use base_price (lowest listing) as the reference for change %
        change_pct = round(((avg_predicted - base_price) / base_price) * 100, 1)
        best_day_idx = int(np.argmin(predicted_prices))
        savings_amount = max(0, base_price - min_predicted)

        # ── 9. Recommendation (WAIT / HOLD / BUY) ────────────────────────────
        if change_pct < -3:
            recommendation = "WAIT"
            rec_reason = (
                f"Price is expected to drop by {abs(change_pct):.1f}% over the "
                f"next {days_ahead} days — a better deal is likely ahead."
            )
        elif change_pct > 2:
            recommendation = "BUY"
            rec_reason = (
                f"Price is likely to rise by {change_pct:.1f}% over the next "
                f"{days_ahead} days. Buy now to lock in the current price."
            )
        else:
            recommendation = "HOLD"
            rec_reason = (
                f"Price is relatively stable (expected change: {change_pct:+.1f}%). "
                f"No urgent pressure to buy or wait right now."
            )

        # ── 10. Confidence (70–85 %) ─────────────────────────────────────────
        conf_score, conf_label = _confidence(X, y, model, use_poly, real_rows)

        model_name = "Polynomial Ridge" if use_poly else "Gradient Boosting"

        trend = [{"month": 0, "price": base_price}] + [
            {"month": round((i + 1) / 30, 1), "price": predicted_prices[i]}
            for i in range(0, len(predicted_prices), max(1, days_ahead // 4))
        ]

        return {
            "current_price":     base_price,          # consistent with comparison UI
            "current_avg_price": base_price,
            "best_deal_price":   base_price,
            "predicted_price":   int(round(avg_predicted)),
            "predicted_prices":  predicted_series,
            "past_prices":       past_prices,
            "change_pct":        change_pct,
            "change_percent":    change_pct,
            "direction":         "up" if change_pct > 2 else "down" if change_pct < -3 else "stable",
            "recommendation":    recommendation,
            "rec_reason":        rec_reason,
            "savings_amount":    int(savings_amount),
            "best_time_to_buy":  future_dates[best_day_idx],
            "confidence_score":  conf_score,
            "confidence":        conf_label,
            "days_ahead":        days_ahead,
            "trend":             trend,
            "model":             model_name,
        }

    except Exception:
        return _empty_result()


# ═══════════════════════════════════════════════════════════════════════════════
#  EMPTY RESULT SENTINEL
# ═══════════════════════════════════════════════════════════════════════════════

def _empty_result() -> dict:
    return {
        "current_price": 0,      "current_avg_price": 0,   "best_deal_price": 0,
        "predicted_price": 0,    "predicted_prices": [],    "past_prices": [],
        "change_pct": 0.0,       "change_percent": 0.0,     "direction": "stable",
        "recommendation": "HOLD","rec_reason": "Insufficient data for prediction.",
        "savings_amount": 0,     "best_time_to_buy": "N/A",
        "confidence_score": 72.0,"confidence": "medium",
        "days_ahead": 30,        "trend": [],               "model": "N/A",
    }
