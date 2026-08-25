"""Generate a 250-event evaluation dataset covering all 9 taxonomy failure classes."""
import json
import random
from pathlib import Path

random.seed(42)

TAXONOMY = [
    {"reason": "insufficient_funds",        "weight": 0.35, "lo": 50000,   "hi": 2000000},
    {"reason": "temporary_network_timeout", "weight": 0.25, "lo": 10000,   "hi": 500000},
    {"reason": "gateway_timeout",           "weight": 0.10, "lo": 10000,   "hi": 500000},
    {"reason": "card_expired",              "weight": 0.10, "lo": 10000,   "hi": 100000},
    {"reason": "suspected_fraud",           "weight": 0.05, "lo": 1000000, "hi": 10000000},
    {"reason": "token_invalid",             "weight": 0.05, "lo": 10000,   "hi": 100000},
    {"reason": "mandate_revoked",           "weight": 0.04, "lo": 10000,   "hi": 100000},
    {"reason": "checkout_abandoned",        "weight": 0.03, "lo": 50000,   "hi": 1000000},
    {"reason": "do_not_honour",             "weight": 0.03, "lo": 100000,  "hi": 500000},
]

dataset = []
for i in range(250):
    t = random.choices(TAXONOMY, weights=[x["weight"] for x in TAXONOMY])[0]
    dataset.append({
        "payment_id": f"pay_eval_{i:04d}",
        "customer_id": f"cust_eval_{random.randint(1, 80)}",
        "amount": random.randint(t["lo"], t["hi"]),
        "failure_reason": t["reason"],
        "retry_count": random.randint(0, 3),
    })

out = Path("evaluation/datasets/labeled_failures.json")
out.parent.mkdir(parents=True, exist_ok=True)
with open(out, "w") as f:
    json.dump(dataset, f, indent=2)

print(f"✓ Generated {len(dataset)} events → {out}")
