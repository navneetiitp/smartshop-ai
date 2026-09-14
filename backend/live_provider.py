"""Live Google Shopping provider through SerpApi.

The provider is optional. If SERPAPI_KEY is absent, callers can use the
bundled historical catalog. Live results are never synthesized.
"""

from __future__ import annotations

import hashlib
import os
import re
import threading
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import requests

SERPAPI_URL = "https://serpapi.com/search.json"
CACHE_SECONDS = 300
REQUEST_TIMEOUT = (5, 8)
_CACHE: dict[tuple, tuple[float, dict]] = {}
_CACHE_LOCK = threading.Lock()

STORE_ALIASES = {
    "amazon": ("amazon",),
    "flipkart": ("flipkart",),
    "bestbuy": ("bestbuy", "best buy"),
    "ebay": ("ebay", "e bay"),
}
STORE_DOMAINS = {
    "amazon": ("amazon.", "amazon.com"),
    "flipkart": ("flipkart.com",),
    "bestbuy": ("bestbuy.com",),
    "ebay": ("ebay.", "ebay.com"),
}
STORE_LABELS = {
    "amazon": "Amazon",
    "flipkart": "Flipkart",
    "bestbuy": "Best Buy",
    "ebay": "eBay",
}


def is_configured() -> bool:
    return bool(os.getenv("SERPAPI_KEY", "").strip())


def _safe_url(value: Any) -> str:
    text = str(value or "").strip()
    try:
        parsed = urlparse(text)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return text
    except Exception:
        pass
    return "#"


def _parse_price(value: Any) -> float | None:
    if value is None:
        return None
    match = re.search(r"-?\d+(?:[.,]\d+)*(?:\.\d+)?", str(value).replace("₹", "").replace("$", "").replace("€", ""))
    if not match:
        return None
    raw = match.group(0).replace(",", "")
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if value > 0 else None


def _cache_get(key: tuple) -> dict | None:
    with _CACHE_LOCK:
        item = _CACHE.get(key)
        if item is None:
            return None
        expires, payload = item
        if expires <= time.time():
            _CACHE.pop(key, None)
            return None
        return payload


def _cache_set(key: tuple, payload: dict) -> None:
    with _CACHE_LOCK:
        _CACHE[key] = (time.time() + CACHE_SECONDS, payload)
        if len(_CACHE) > 100:
            for old_key, _ in sorted(_CACHE.items(), key=lambda item: item[1][0])[:20]:
                _CACHE.pop(old_key, None)


def _website_terms(website: str) -> tuple[str, ...]:
    wanted = (website or "all").strip().lower()
    if wanted == "all" or not wanted:
        return ()
    return STORE_ALIASES.get(wanted, (wanted,))


def _matches_website(row: dict, website: str) -> bool:
    terms = _website_terms(website)
    if not terms:
        return True
    source = str(row.get("website", "")).lower()
    link = str(row.get("product_link", "")).lower()
    if any(term in source for term in terms):
        return True
    domains = STORE_DOMAINS.get((website or "").strip().lower(), ())
    return any(domain in link for domain in domains)


def _fingerprint(title: str, source: str, link: str) -> str:
    raw = f"{title}|{source}|{link}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _parse_results(payload: dict, now: str, gl: str) -> list[dict]:
    results: list[dict] = []
    seen: set[str] = set()
    for item in payload.get("shopping_results") or []:
        if not isinstance(item, dict):
            continue
        price = item.get("extracted_price")
        if price is None:
            price = _parse_price(item.get("price"))
        try:
            price = float(price)
        except (TypeError, ValueError):
            continue
        if price <= 0:
            continue

        title = str(item.get("title") or "Laptop listing").strip()
        source = str(item.get("source") or "Unknown seller").strip()
        link = _safe_url(item.get("product_link") or item.get("link"))
        fingerprint = _fingerprint(title, source, link)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)

        rating = item.get("rating")
        try:
            rating_num = float(rating) if rating is not None else None
            if rating_num is not None and not 0 <= rating_num <= 5:
                rating_num = None
        except (TypeError, ValueError):
            rating_num = None

        results.append({
            "id": f"live-{fingerprint}",
            "product_name": title,
            "product_description": (
                "Live Google Shopping listing. Price, seller, shipping and "
                "availability can change; verify the destination before buying."
            ),
            "price": int(round(price)),
            "currency": "INR" if gl == "in" else "LOCAL",
            "ratings_num": rating_num,
            "ratings": f"{rating_num:.1f}" if rating_num is not None else "Not Available",
            "reviews": f"{item.get('reviews')} reviews" if item.get("reviews") is not None else "Live listing",
            "product_link": link,
            "image_link": _safe_url(item.get("thumbnail")),
            "website": source,
            "date": now,
            "data_source": "live",
            "observed_at": now,
            "old_price": item.get("old_price"),
            "delivery": item.get("delivery"),
            "condition": item.get("second_hand_condition"),
            "position": item.get("position"),
        })
    return results


def _request(query: str, limit: int, gl: str, hl: str, google_domain: str) -> dict:
    key = os.getenv("SERPAPI_KEY", "").strip()
    params = {
        "engine": "google_shopping",
        "q": query,
        "gl": gl,
        "hl": hl,
        "google_domain": google_domain,
        "api_key": key,
        "num": limit,
    }
    try:
        response = requests.get(SERPAPI_URL, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        raise RuntimeError(f"SerpApi request failed with HTTP {status}") from exc
    except requests.RequestException as exc:
        raise RuntimeError(f"SerpApi request failed: {exc}") from exc
    except ValueError as exc:
        raise RuntimeError("SerpApi returned invalid JSON") from exc

    if payload.get("error"):
        raise RuntimeError(f"SerpApi error: {payload['error']}")
    return payload


def search_live(query: str, limit: int = 20, website: str = "all") -> dict:
    if not is_configured():
        raise RuntimeError("SERPAPI_KEY is not configured")

    query = " ".join(str(query or "laptop").split()) or "laptop"
    limit = min(max(int(limit), 1), 40)
    gl = os.getenv("SERPAPI_GL", "in").strip().lower() or "in"
    hl = os.getenv("SERPAPI_HL", "en").strip() or "en"
    google_domain = os.getenv("SERPAPI_GOOGLE_DOMAIN", "google.co.in").strip() or "google.co.in"
    wanted = (website or "all").strip().lower() or "all"

    cache_key = (query.lower(), gl, hl, google_domain, limit, wanted)
    cached = _cache_get(cache_key)
    if cached is not None:
        return {**cached, "cached": True}

    now = datetime.now(timezone.utc).isoformat()
    payload = _request(query, limit, gl, hl, google_domain)
    results = _parse_results(payload, now, gl)

    # A first-page Shopping query can contain few or no listings from the
    # requested retailer. Make a retailer-qualified request when coverage is
    # weak, then filter by the actual seller/source or retailer domain. Never
    # substitute historical or unrelated data.
    filtered = [r for r in results if _matches_website(r, wanted)]
    actual_query = query
    if wanted != "all" and len(filtered) < 3:
        label = STORE_LABELS.get(wanted, wanted)
        domain = {"amazon": "amazon.in", "flipkart": "flipkart.com", "bestbuy": "bestbuy.com", "ebay": "ebay.com"}.get(wanted)
        qualified_queries = [f"{query} {label}"]
        if domain:
            qualified_queries.append(f"site:{domain} {query}")
        for qualified_query in qualified_queries:
            qualified_key = (qualified_query.lower(), gl, hl, google_domain, limit, wanted)
            qualified_cached = _cache_get(qualified_key)
            if qualified_cached is None:
                qnow = datetime.now(timezone.utc).isoformat()
                qpayload = _request(qualified_query, limit, gl, hl, google_domain)
                qresults = _parse_results(qpayload, qnow, gl)
                qualified_cached = {
                    "results": qresults,
                    "query": qualified_query,
                    "observed_at": qnow,
                    "provider": "Google Shopping via SerpApi",
                    "location": gl,
                    "cached": False,
                }
                _cache_set(qualified_key, qualified_cached)
            extra = [r for r in qualified_cached["results"] if _matches_website(r, wanted)]
            if len(extra) > len(filtered):
                filtered = extra
                actual_query = qualified_query
            if len(filtered) >= 3:
                break

    final_results = filtered if wanted != "all" else results
    response = {
        "results": final_results,
        "query": query,
        "total": len(final_results),
        "observed_at": now,
        "provider": "Google Shopping via SerpApi",
        "location": gl,
        "cached": False,
        "cache_seconds": CACHE_SECONDS,
        "website": wanted,
        "provider_query": actual_query,
    }
    _cache_set(cache_key, response)
    return response
