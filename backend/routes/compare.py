from flask import Blueprint, jsonify, request
from ml.ai_score import score_dataframe
from utils.data_loader import get_dataframe
from live_provider import is_configured, search_live
from utils.live_history import record_observations
import pandas as pd
import re

compare_bp = Blueprint("compare", __name__)

_GENERIC = {
    "laptop", "notebook", "computer", "pc", "desktop", "screen", "display",
    "inch", "inches", "gb", "tb", "ssd", "hdd", "ram", "fhd", "hd", "full",
    "windows", "home", "pro", "new", "thin", "light", "and", "with", "for",
    "the", "intel", "amd", "core", "processor", "generation", "gen", "series",
    "edition", "model", "version", "touch", "touchscreen", "led", "wifi",
}
_BRANDS = {"dell", "hp", "apple", "lenovo", "asus", "acer", "msi", "samsung", "microsoft", "razer", "lg", "gigabyte", "honor", "realme", "xiaomi"}


def _safe_image(url) -> str:
    value = str(url or "").strip()
    return value if value.lower().startswith(("http://", "https://")) else "https://placehold.co/400x300/1e293b/94a3b8?text=No+Image"


def _price_explanation(best_price_item: dict, listings: list) -> str:
    if not listings:
        return "Lowest price among the available listings."
    savings = max(l["price"] for l in listings) - best_price_item["price"]
    if savings > 0:
        return f"Lowest price among the available listings. Save ₹{savings:,} versus the highest listing."
    return "Lowest price among the available listings."


def _value_explanation(best_value_item: dict) -> str:
    score = best_value_item.get("value_score", best_value_item.get("ai_score", 0))
    rating = best_value_item.get("ratings_num")
    rating_text = f"rated {rating:.1f}★" if rating else "without a verified rating"
    return f"Best value among these live listings. Value Score {score:.0f}/100 — {rating_text}."


def _build_response(name: str, results: list, note: str | None = None) -> dict:
    results = sorted(results, key=lambda x: (x.get("price", 0), x.get("website", "")))
    if not results:
        return {
            "name": name, "listings": [], "best_deal": None, "best_value": None,
            "price_range": {"min": 0, "max": 0, "savings": 0},
            "data_mode": "live" if note else "historical",
            **({"comparison_note": note} if note else {}),
        }

    min_price = results[0]["price"]
    max_price = results[-1]["price"]
    cheapest = [r for r in results if r["price"] == min_price]
    best_deal = max(cheapest, key=lambda x: x.get("value_score", x.get("ai_score", 0)))
    best_value = max(results, key=lambda x: (x.get("value_score", x.get("ai_score", 0)), -x["price"]))

    for r in results:
        is_deal = r["id"] == best_deal["id"]
        is_value = r["id"] == best_value["id"]
        r["badge"] = "both" if is_deal and is_value else "best_deal" if is_deal else "best_value" if is_value else None

    best_deal_out = dict(best_deal)
    best_deal_out.update({
        "is_best_deal": True,
        "badge": "both" if best_deal["id"] == best_value["id"] else "best_deal",
        "deal_explanation": _price_explanation(best_deal, results),
    })
    best_value_out = dict(best_value)
    best_value_out.update({
        "is_best_value": True,
        "badge": "both" if best_deal["id"] == best_value["id"] else "best_value",
        "value_explanation": _value_explanation(best_value),
    })

    response = {
        "name": name,
        "listings": results,
        "best_deal": best_deal_out,
        "best_value": best_value_out,
        "price_range": {"min": min_price, "max": max_price, "savings": max_price - min_price},
        "data_mode": results[0].get("data_source", "historical"),
    }
    if note:
        response["comparison_note"] = note
    return response


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in re.findall(r"[a-z0-9]+", str(text).lower()) if len(t) >= 2]


def _core_tokens(name: str) -> list[str]:
    return list(dict.fromkeys(t for t in _tokens(name) if t not in _GENERIC))


def _identity_tokens(name: str) -> list[str]:
    """Prefer model identifiers and other distinctive tokens for cross-store matching."""
    tokens = _core_tokens(name)
    model = [t for t in tokens if any(ch.isdigit() for ch in t)]
    brand = [t for t in tokens if t in _BRANDS]
    distinctive = [t for t in tokens if len(t) >= 6 and t not in _BRANDS]
    ordered = []
    for t in brand + model + distinctive:
        if t not in ordered:
            ordered.append(t)
    return ordered


def _relevance_score(candidate_name: str, requested_name: str) -> int:
    wanted = set(_core_tokens(requested_name))
    candidate = set(_tokens(candidate_name))
    if not wanted:
        return 1

    overlap = wanted & candidate
    wanted_brand = wanted & _BRANDS
    if wanted_brand and not (wanted_brand & candidate):
        return -100

    identity = set(_identity_tokens(requested_name))
    identity_overlap = identity & candidate
    score = len(overlap)
    score += 5 * len(identity_overlap)
    if wanted_brand and (wanted_brand & candidate):
        score += 8
    return score


def _is_relevant(candidate_name: str, requested_name: str) -> bool:
    score = _relevance_score(candidate_name, requested_name)
    if score < 0:
        return False
    identity = set(_identity_tokens(requested_name))
    candidate = set(_tokens(candidate_name))
    identity_overlap = identity & candidate
    wanted_brand = set(_core_tokens(requested_name)) & _BRANDS

    # If a model identifier exists, require at least one model identifier and
    # the same brand. This avoids comparing a Dell monitor with a Dell laptop.
    model_tokens = {t for t in identity if any(ch.isdigit() for ch in t)}
    if model_tokens:
        if not (model_tokens & candidate):
            return False
        if wanted_brand and not (wanted_brand & candidate):
            return False
        return True

    # For names without model identifiers, require two meaningful overlaps,
    # or one long distinctive token plus the brand.
    return len(identity_overlap) >= 2 or (len(identity_overlap) >= 1 and bool(wanted_brand & candidate))


def _comparison_queries(name: str) -> list[str]:
    text = " ".join(str(name or "").split())
    identity = _identity_tokens(text)
    core = _core_tokens(text)
    queries = [text]
    if identity:
        queries.append(" ".join(identity[:7]))
        if len(identity) >= 3:
            queries.append(" ".join(identity[:4]))
    elif core:
        queries.append(" ".join(core[:6]))
        queries.append(" ".join(core[:4]))
    return list(dict.fromkeys(q for q in queries if q))


def _live_listing(row: dict) -> dict:
    rating = row.get("ratings_num")
    score = round(float(rating) / 5.0 * 100.0, 1) if rating is not None else 0.0
    return {
        "id": str(row.get("id", "")),
        "product_name": str(row.get("product_name", "N/A")),
        "price": int(row.get("price", 0)),
        "currency": "INR",
        "ratings": str(row.get("ratings", "Not Available")),
        "ratings_num": float(rating) if rating is not None else None,
        "reviews": str(row.get("reviews", "Live listing")),
        "product_link": str(row.get("product_link", "#")),
        "image_link": _safe_image(row.get("image_link")),
        "website": str(row.get("website", "Unknown")),
        "value_score": score,
        "ai_score": score,
        "data_source": "live",
    }


def _append_unique(rows: list, seen: set, candidates: list) -> None:
    for row in candidates:
        if not _is_relevant(row.get("product_name", ""), row.get("_requested_name", "")):
            continue
        rid = str(row.get("id", ""))
        link = str(row.get("product_link", ""))
        key = link if link and link != "#" else rid
        if key and key not in seen:
            seen.add(key)
            rows.append(row)


@compare_bp.route("/compare")
def compare():
    name = " ".join(request.args.get("name", "").split())
    if not name:
        return jsonify({"error": "Product name required"}), 400

    current_price = request.args.get("current_price", type=float)
    if current_price is not None and current_price <= 0:
        current_price = None
    current_website = request.args.get("current_website", "").strip()
    current_link = request.args.get("current_link", "").strip()
    current_data_source = request.args.get("current_data_source", "historical").strip().lower()
    if current_data_source not in {"live", "historical"}:
        current_data_source = "historical"

    if is_configured():
        live_error = None
        try:
            rows = []
            seen = set()
            for comparison_query in _comparison_queries(name):
                payload = search_live(comparison_query, limit=40)
                candidates = []
                for row in payload.get("results", []):
                    row = dict(row)
                    row["_requested_name"] = name
                    candidates.append(row)
                _append_unique(rows, seen, candidates)
                # A useful comparison has at least two listings; collect a few
                # more before stopping, but avoid unnecessary paid requests.
                if len(rows) >= 8:
                    break

            # If the exact/model query produced only the selected store, make a
            # targeted pass for other major retailers. This is especially useful
            # when Google Shopping's first page is dominated by one seller.
            stores = ["amazon", "flipkart", "bestbuy", "ebay"]
            present = {str(r.get("website", "")).lower() for r in rows}
            for store in stores:
                if len(rows) >= 12:
                    break
                if any(store in source for source in present):
                    continue
                try:
                    # Use the compact model-identity query for retailer-specific
                    # discovery. Exact Shopping titles often contain seller-
                    # specific wording and are less reliable across stores.
                    targeted_query = _comparison_queries(name)[1] if len(_comparison_queries(name)) > 1 else name
                    payload = search_live(targeted_query, limit=40, website=store)
                except Exception as exc:
                    live_error = live_error or str(exc)
                    continue
                candidates = []
                for row in payload.get("results", []):
                    row = dict(row)
                    row["_requested_name"] = name
                    candidates.append(row)
                _append_unique(rows, seen, candidates)
                present = {str(r.get("website", "")).lower() for r in rows}

            # Always include the exact card selected by the user. It is a real
            # observation even when no cross-store alternative is returned.
            if current_data_source == "live" and current_price is not None:
                current_key = current_link if current_link.startswith(("http://", "https://")) else ""
                if not any(current_key and r.get("product_link") == current_key for r in rows):
                    rows.insert(0, {
                        "id": "current-listing",
                        "product_name": name,
                        "price": current_price,
                        "ratings_num": None,
                        "ratings": "Not Available",
                        "reviews": "Current live listing",
                        "product_link": current_key or "#",
                        "image_link": "",
                        "website": current_website or "Current listing",
                        "currency": "INR",
                        "observed_at": pd.Timestamp.utcnow().isoformat(),
                        "_requested_name": name,
                    })

            rows = [r for r in rows if float(r.get("price", 0) or 0) > 0]
            if rows:
                try:
                    record_observations(rows)
                except Exception as exc:
                    # History persistence must never make an otherwise valid
                    # live comparison fail.
                    live_error = live_error or f"History storage warning: {exc}"
                results = [_live_listing(row) for row in rows]
                response = _build_response(name, results)
                response["search_query"] = name
                response["retailers_found"] = sorted({r["website"] for r in results})
                if len(results) == 1:
                    response["comparison_note"] = "Only one relevant live listing was returned; no prices were invented."
                elif live_error:
                    response["comparison_note"] = "Comparison uses the relevant live listings that were successfully returned."
                return jsonify(response)

            return jsonify({
                "name": name,
                "listings": [],
                "best_deal": None,
                "best_value": None,
                "price_range": {"min": 0, "max": 0, "savings": 0},
                "data_mode": "live",
                "comparison_note": "No relevant live listings were returned for this product.",
            })

        except Exception as exc:
            live_error = str(exc)

    # Provider unavailable: historical comparison is explicitly marked.
    df = score_dataframe(get_dataframe())
    mask = df["product_name"].str.lower().str.contains(re.escape(name.lower()), na=False, regex=True)
    matches = df[mask]
    if matches.empty:
        payload = {
            "error": "No products found",
            "name": name,
            "data_mode": "historical_fallback" if live_error else "historical",
        }
        if live_error:
            payload["live_error"] = live_error
        # If a real current listing was supplied, don't turn a transient live
        # error into a misleading 404. Return the selected listing instead.
        if current_data_source == "live" and current_price is not None:
            fallback = _live_listing({
                "id": "current-listing",
                "product_name": name,
                "price": current_price,
                "ratings_num": None,
                "ratings": "Not Available",
                "reviews": "Current live listing",
                "product_link": current_link or "#",
                "website": current_website or "Current listing",
            })
            response = _build_response(name, [fallback], "Live alternatives could not be loaded; showing the selected live listing only.")
            response["data_mode"] = "live_partial"
            return jsonify(response)
        return jsonify(payload), 404

    results = []
    for _, row in matches.iterrows():
        score = float(row["ai_score"])
        results.append({
            "id": int(row["id"]),
            "product_name": str(row["product_name"]),
            "price": int(row["price"]),
            "currency": "INR",
            "ratings": str(row["ratings"]),
            "ratings_num": float(row["ratings_num"]) if pd.notna(row["ratings_num"]) else None,
            "reviews": str(row["reviews"]),
            "product_link": str(row["product_link"]),
            "image_link": _safe_image(row["image_link"]),
            "website": str(row["website"]),
            "value_score": score,
            "ai_score": score,
            "data_source": "historical",
        })

    payload = _build_response(name, results)
    if live_error:
        payload["live_error"] = live_error
        payload["data_mode"] = "historical_fallback"
    return jsonify(payload)
