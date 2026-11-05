"""Compare tracker snapshots locally; network access and writes belong to the agent."""
import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path


FIELDS = ("regular_price", "sale_price", "has_credit")
READABLE = {"read_cached", "read_live", "read_freshness_unknown"}


def index_snapshot(snapshot):
    if snapshot.get("schema_version") != 1 or not snapshot.get("currency"):
        raise ValueError("Unsupported snapshot schema or missing currency")
    result = {}
    for item in snapshot["items"]:
        url = item["url"]
        if not isinstance(url, str) or not url.startswith(("https://", "http://")) or url in result:
            raise ValueError("Invalid or duplicate URL")
        for key in FIELDS[:2]:
            value = item[key]
            if value is not None and (type(value) not in (int, float) or not Decimal(str(value)).is_finite() or value <= 0):
                raise ValueError("Invalid price")
        if type(item["has_credit"]) is not bool:
            raise ValueError("Invalid has_credit")
        if item["sale_price"] is not None and item["regular_price"] is not None and item["sale_price"] >= item["regular_price"]:
            raise ValueError("Sale price must be below regular price")
        result[url] = item
    return result


def compare(previous, current, threshold):
    new = index_snapshot(current)
    result = {"first_run": previous is None, "raw_diff": [], "significant_changes": [], "diagnostics": []}
    if previous is None:
        return result
    old = index_snapshot(previous)
    if previous["currency"] != current["currency"]:
        raise ValueError("Currency changed; snapshots cannot be compared")
    for url in sorted(old.keys() | new.keys()):
        before, after = old.get(url), new.get(url)
        item = after or before
        base = {"url": url, "name": item["name"]}
        if before is None or after is None:
            change = {**base, "reasons": ["product_added" if before is None else "product_removed"]}
            result["raw_diff"].append(change)
            if item.get("source_status") in READABLE:
                result["significant_changes"].append(change)
            else:
                result["diagnostics"].append({**base, "reason": "unavailable_product"})
            continue
        fields = {key: {"before": before[key], "after": after[key]} for key in FIELDS if before[key] != after[key]}
        if fields:
            result["raw_diff"].append({**base, "fields": fields})
        if any(before.get(key) != after.get(key) for key in ("region", "price_basis", "sku")):
            result["diagnostics"].append({**base, "reason": "comparison_context_changed"})
            continue
        if before.get("source_status") not in READABLE or after.get("source_status") not in READABLE:
            result["diagnostics"].append({**base, "reason": "unavailable_or_unverified_data"})
            continue
        reasons = []
        for key in FIELDS[:2]:
            if key not in fields:
                continue
            a, b = before[key], after[key]
            if a is not None and b is not None:
                percent = (Decimal(str(b)) - Decimal(str(a))) / Decimal(str(a)) * 100
                fields[key]["percent"] = float(percent)
                if abs(percent) >= threshold:
                    reasons.append(key + "_threshold")
            elif key == "sale_price" and before["regular_price"] is not None and after["regular_price"] is not None:
                reasons.append("sale_started" if b is not None else "sale_ended")
            else:
                result["diagnostics"].append({**base, "reason": key + "_unknown_transition"})
        if "has_credit" in fields:
            reasons.append("credit_changed")
        if reasons:
            result["significant_changes"].append({**base, "fields": fields, "reasons": reasons,
                "cached": before.get("source_status") == "read_cached" or after.get("source_status") == "read_cached"})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("previous", type=Path)
    parser.add_argument("current", type=Path)
    parser.add_argument("--knowledge", type=Path, default=Path("KNOWLEDGE.md"))
    args = parser.parse_args()
    try:
        policy_text = args.knowledge.read_text().split("<!-- diff-policy -->", 1)[1].split("```json", 1)[1].split("```", 1)[0]
        threshold = Decimal(str(json.loads(policy_text)["price_change_percent"]))
        if not threshold.is_finite() or threshold <= 0:
            raise ValueError("Invalid significance threshold")
        result = compare(json.loads(args.previous.read_text()), json.loads(args.current.read_text()), threshold)
    except (ValueError, KeyError, TypeError, IndexError, AttributeError, OSError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
