"""Score Gemini's recorded answers against the answer key, and your own logging. No Gemini calls."""
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from getpass import getpass
from pathlib import Path

import db

GOLD = json.loads(Path("data/gold.json").read_text(encoding="utf-8"))["photos"]
DISHES = json.loads(Path("data/menu.json").read_text(encoding="utf-8"))["dishes"]
GROUP = {name: dish["group"] for name, dish in DISHES.items()}
NOT_A_DISH = {"salad", "condiment"}
CREDIT = {"exact": 1.0, "look-alike": 0.5, "unknown": 1.0}


def same(item, key_item, kind):
    """Does the model's item match this answer-key item, in this kind of match?"""
    if kind == "unknown":
        return key_item.get("unknown", False) and GROUP.get(item["dish"]) not in NOT_A_DISH
    if key_item.get("unknown"):
        return False
    if kind == "exact":
        return item["dish"] in key_item["names"]
    return GROUP.get(item["dish"]) in {GROUP[n] for n in key_item["names"]}


def match(said, key):
    """Pair answer-key items with the model's items, each used once: exact names first, then look-alikes, then unknowns."""
    free, pairs = list(said), []
    for kind in CREDIT:
        for key_item in key:
            if any(key_item is k for _, k, _ in pairs):
                continue
            item = next((i for i in free if same(i, key_item, kind)), None)
            if item is not None:
                free.remove(item)
                pairs.append((item, key_item, kind))
    return pairs


def benchmark(folder="records"):
    """Recall, precision, count accuracy and tokens, over every photo that has a recorded answer."""
    points = key_items = said_items = matched = 0
    counts, tokens, missed = [], [], []
    for stem, answer in GOLD.items():
        record = Path(folder) / f"{stem}.json"
        if not record.exists():
            continue
        saved = json.loads(record.read_text(encoding="utf-8"))
        said, key = saved["reading"]["items"], answer["items"]
        pairs = match(said, key)
        points += sum(CREDIT[kind] for _, _, kind in pairs)
        key_items += len(key)
        said_items += len(said)
        matched += len(pairs)
        counts += [item["unit"] == "piece" and item["amount"] == k["amount"]
                   for item, k, kind in pairs
                   if kind != "unknown" and k["unit"] == "piece" and GROUP[k["names"][0]] not in NOT_A_DISH]
        found = [k for _, k, _ in pairs]
        missed += [f"{stem[:2]} {'unknown' if k.get('unknown') else k['names'][0]}"
                   for k in key if not any(k is f for f in found)]
        tokens.append(saved["tokens"]["in"] + saved["tokens"]["out"] + saved["tokens"]["thinking"])
    if not tokens:
        return {"photos scored": 0}
    return {"photos scored": len(tokens),
            "dish recall %": round(100 * points / key_items),
            "dish precision %": round(100 * matched / said_items),
            "count accuracy %": round(100 * sum(counts) / len(counts)) if counts else None,
            "tokens per photo": round(statistics.mean(tokens)),
            "missed": missed}


def your_logging(email, password):
    """From your own photo meals: dishes kept as suggested, and corrections per meal, day by day."""
    database = db.connect()
    db.sign_in(database, email, password)
    since = datetime.now().astimezone() - timedelta(days=60)
    meals = [m for m in db.meals_since(database, since) if not m["photo"].startswith("again-")]
    items = [i for m in meals for i in m["meal_items"] if i.get("model_dish")]
    by_day = defaultdict(list)
    for meal in meals:
        day = datetime.fromisoformat(meal["eaten_at"]).astimezone().strftime("%m/%d")
        by_day[day].append(sum(1 for i in meal["meal_items"] if i.get("model_dish") and i["dish"] != i["model_dish"]))
    return {"photo meals": len(meals),
            "kept as suggested %": round(100 * sum(i["dish"] == i["model_dish"] for i in items) / len(items)) if items else None,
            "corrections per meal, by day": {day: round(statistics.mean(c), 2) for day, c in by_day.items()}}


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "records"
    results = benchmark(folder)
    if folder == "records":
        print("Log in with your ThaliTrack account (the password won't show as you type).")
        results.update(your_logging(input("Email: "), getpass("Password: ")))
    for name, value in results.items():
        print(f"{name:30} {value}")
    Path("results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("\nSaved results.json")
