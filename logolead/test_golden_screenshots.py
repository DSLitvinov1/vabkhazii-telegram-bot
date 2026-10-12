"""Regression gate: every screenshot buyer request must meet delivery threshold.

This is only classification testing; NEVER send fixture data to Telegram.
"""
from golden_screenshots import GOLDEN_TELEGRAM, GOLDEN_PROFI, NEGATIVE_CASES
from classifier import score, score_market_order

MIN_SCORE = 60
for item in GOLDEN_TELEGRAM:
    points, reasons = score(item["text"])
    assert points >= MIN_SCORE, (item["id"], points, reasons)

for item in GOLDEN_PROFI:
    points, reasons = score_market_order(item["text"], item["source"])
    assert points >= MIN_SCORE, (item["id"], points, reasons)

for text in NEGATIVE_CASES:
    points, reasons = score(text)
    assert points == 0, (text, points, reasons)

assert all(not item.get("verified_source_url") for item in GOLDEN_TELEGRAM)
assert all("verified_source_url" not in item for item in GOLDEN_PROFI)
print("GOLDEN_SCREENSHOTS_OK",
      "telegram", len(GOLDEN_TELEGRAM),
      "profi", len(GOLDEN_PROFI),
      "negative", len(NEGATIVE_CASES))
