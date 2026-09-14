"""Conservative price forecasting using only real observed prices."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_percentage_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures

from ..utils.live_history import history_for_product


def _empty(reason: str, current_price: float | int | None = None,
           observation_count: int = 0, observation_days: int = 0) -> dict:
    current = float(current_price) if current_price is not None and float(current_price) > 0 else None
    return {
        "current_price": int(round(current)) if current is not None else None,
        "current_avg_price": int(round(current)) if current is not None else None,
        "best_deal_price": int(round(current)) if current is not None else None,
        "predicted_price": None,
        "predicted_prices": [],
        "past_prices": [],
        "change_pct": None,
        "change_percent": None,
        "direction": "stable",
        "recommendation": "INSUFFICIENT DATA",
        "rec_reason": reason,
        "savings_amount": 0,
        "best_time_to_buy": "N/A",
        "confidence_score": None,
        "confidence": "low",
        "days_ahead": 30,
        "trend": [],
        "model": "N/A",
        "data_quality": "insufficient",
        "observation_count": int(observation_count),
        "observation_days": int(observation_days),
    }


def _daily_history(history: pd.DataFrame) -> pd.DataFrame:
    if history.empty:
        return history
    history = history.copy()
    history["date"] = pd.to_datetime(history["date"], errors="coerce")
    history["price"] = pd.to_numeric(history["price"], errors="coerce")
    history = history.dropna(subset=["date", "price"])
    history = history[history["price"] > 0]
    if history.empty:
        return history
    # Multiple stores/listings observed on the same day are one market
    # snapshot. Use the median rather than treating each seller as a new day.
    history["calendar_date"] = history["date"].dt.normalize()
    daily = (
        history.groupby("calendar_date", as_index=False)["price"]
        .median()
        .rename(columns={"calendar_date": "date"})
        .sort_values("date")
    )
    return daily.reset_index(drop=True)


def _prepare_live_history(product_name: str) -> pd.DataFrame:
    rows = history_for_product(product_name)
    if not rows:
        return pd.DataFrame(columns=["date", "price"])
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["observed_at"], errors="coerce", utc=True).dt.tz_localize(None)
    return _daily_history(df)


def _fit(history: pd.DataFrame):
    history = history.sort_values("date").copy()
    history["day"] = (history["date"] - history["date"].min()).dt.total_seconds() / 86400.0
    X = history[["day"]].to_numpy(dtype=float)
    y = history["price"].to_numpy(dtype=float)

    if len(history) >= 8 and history["day"].nunique() >= 4:
        model = make_pipeline(
            PolynomialFeatures(degree=2, include_bias=False),
            Ridge(alpha=1.0),
        )
        model_name = "Ridge Polynomial Regression"
    else:
        model = LinearRegression()
        model_name = "Linear Regression"

    model.fit(X, y)
    fitted = model.predict(X)
    mape = float(mean_absolute_percentage_error(y, fitted) * 100)
    confidence = round(max(35.0, min(90.0, 90.0 - mape * 2.5)), 1)
    return model, model_name, confidence


def predict_future_price(product_name: str, df: pd.DataFrame,
                         days_ahead: int = 30,
                         current_price: float | int | None = None) -> dict:
    days_ahead = max(7, min(int(days_ahead), 90))
    live = _prepare_live_history(product_name)

    if not live.empty:
        history = live
    else:
        history = df[df["product_name"].astype(str).str.lower() == product_name.lower()].copy()
        history = _daily_history(history)

    unique_days = int(history["date"].dt.date.nunique()) if not history.empty else 0

    # If history exists, prefer the actual latest supplied live-card price for
    # the current-price display. Otherwise use the latest real daily snapshot.
    observed_current = float(history.iloc[-1]["price"]) if not history.empty else None
    display_current = (
        float(current_price) if current_price is not None and float(current_price) > 0
        else observed_current
    )

    if len(history) < 7 or unique_days < 5:
        return _empty(
            "At least 7 real price observations across 5+ different dates are required. "
            "The current price shown above is a real observed listing price; more observations are needed before a forecast is calculated.",
            current_price=display_current,
            observation_count=len(history),
            observation_days=unique_days,
        )

    # A forecast is trained on daily market snapshots, not individual seller
    # rows, to avoid overweighting a day with many listings.
    model, model_name, confidence = _fit(history)
    origin = history["date"].min()
    last_day = float((history["date"].max() - origin).total_seconds() / 86400.0)
    future_day_values = np.array([[last_day + i] for i in range(1, days_ahead + 1)], dtype=float)
    predictions = np.maximum(1.0, model.predict(future_day_values))

    current = observed_current if observed_current is not None else display_current
    if current is None or current <= 0:
        return _empty("A real current price is required before forecasting.", observation_count=len(history), observation_days=unique_days)

    avg_pred = float(np.mean(predictions))
    change_pct = round(((avg_pred - current) / current) * 100, 1)

    if change_pct < -3:
        recommendation = "WAIT"
        reason = f"Observed history/model suggests an average change of {change_pct:.1f}% over the next {days_ahead} days."
    elif change_pct > 2:
        recommendation = "BUY"
        reason = f"Observed history/model suggests prices may rise about {change_pct:.1f}% over the next {days_ahead} days."
    else:
        recommendation = "HOLD"
        reason = f"Observed history/model suggests a relatively small change of {change_pct:+.1f}%."

    past_prices = [
        {"date": row["date"].strftime("%Y-%m-%d"), "price": int(round(row["price"]))}
        for _, row in history.tail(30).iterrows()
    ]
    future_dates = [origin + pd.Timedelta(days=last_day + i) for i in range(1, days_ahead + 1)]
    predicted_prices = [
        {"date": d.strftime("%Y-%m-%d"), "price": int(round(p))}
        for d, p in zip(future_dates, predictions)
    ]
    best_idx = int(np.argmin(predictions))
    min_pred = int(round(predictions[best_idx]))

    return {
        "current_price": int(round(current)),
        "current_avg_price": int(round(current)),
        "best_deal_price": int(round(current)),
        "predicted_price": int(round(avg_pred)),
        "predicted_prices": predicted_prices,
        "past_prices": past_prices,
        "change_pct": change_pct,
        "change_percent": change_pct,
        "direction": "up" if change_pct > 2 else "down" if change_pct < -3 else "stable",
        "recommendation": recommendation,
        "rec_reason": reason,
        "savings_amount": max(0, int(round(current - min_pred))),
        "best_time_to_buy": future_dates[best_idx].strftime("%Y-%m-%d"),
        "confidence_score": confidence,
        "confidence": "high" if confidence >= 75 else "medium" if confidence >= 55 else "low",
        "days_ahead": days_ahead,
        "trend": [],
        "model": model_name,
        "data_quality": "real_observations",
        "observation_count": int(len(history)),
        "observation_days": unique_days,
    }
