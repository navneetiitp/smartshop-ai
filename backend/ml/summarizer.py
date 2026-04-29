import re


REVIEW_LABELS = {
    5: "Excellent",
    4: "Very Good",
    3: "Average",
    2: "Below Average",
    None: "Unrated"
}


def extract_specs(description: str) -> dict:
    specs = {}
    patterns = {
        "processor": r"Processor:\s*([^,]+)",
        "ram": r"RAM:\s*([^,]+)",
        "storage": r"Storage:\s*([^,]+)",
        "os": r"OS:\s*([^,]+)",
        "display": r"Display:\s*([^,]+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            specs[key] = match.group(1).strip()
    return specs


def generate_summary(product_name: str, description: str, price: int,
                     rating: float, review: str, ai_score: float, website: str) -> str:
    specs = extract_specs(description)

    # Rating label
    if rating and rating >= 4.5:
        rating_label = "highly rated"
    elif rating and rating >= 4.0:
        rating_label = "well-rated"
    elif rating and rating >= 3.5:
        rating_label = "moderately rated"
    elif rating:
        rating_label = "lower-rated"
    else:
        rating_label = "currently unrated"

    # Review sentiment label
    review_lower = (review or "").lower()
    if "excellent" in review_lower:
        review_summary = "Customers report excellent performance and premium build quality."
    elif "very good" in review_lower:
        review_summary = "Customers report very good performance and solid build."
    elif "average" in review_lower or "decent" in review_lower:
        review_summary = "Customers find performance adequate for everyday tasks."
    elif "not satisfactory" in review_lower or "poor" in review_lower:
        review_summary = "Some customers have raised concerns about performance."
    else:
        review_summary = "No detailed customer feedback is currently available."

    # Build spec highlights
    spec_parts = []
    if specs.get("processor"):
        spec_parts.append(f"powered by {specs['processor']}")
    if specs.get("ram"):
        spec_parts.append(f"{specs['ram']} RAM")
    if specs.get("storage"):
        spec_parts.append(f"{specs['storage']} storage")
    if specs.get("display"):
        spec_parts.append(f"a {specs['display']} display")

    spec_str = ", ".join(spec_parts) if spec_parts else "detailed specs in description"

    # Build summary
    summary = (
        f"The **{product_name}** is {rating_label} and listed at ₹{price:,} on {website}. "
        f"It features {spec_str}. "
        f"{review_summary} "
        f"Our AI scoring system gives it a score of **{ai_score}/100**, "
        f"factoring in price competitiveness, ratings, and listing recency."
    )
    return summary
