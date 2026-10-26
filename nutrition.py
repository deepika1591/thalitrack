"""Turn dishes and amounts into calories, protein, carbs, fat and fibre."""
import csv

NUTRIENTS = ["kcal", "protein_g", "carbs_g", "fat_g", "fibre_g"]
ML = {"katori": 150, "cup": 240, "tbsp": 15}

TABLE = {}
with open("data/nutrition_table.csv", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        TABLE[row["dish"]] = row

def units_of(dish_unit, amount, unit):
    """How many of the dish's own units is `amount unit`? None if they can't be compared."""
    if unit == dish_unit:
        return amount
    if unit in ML and dish_unit in ML:
        return amount * ML[unit] / ML[dish_unit]
    return None

def nutrients(dish, amount, unit):
    """Nutrients for `amount unit` of a dish, or None if it can't be looked up."""
    row = TABLE.get(dish)
    if row is None:
        return None
    n = units_of(row["unit"], amount, unit)
    if n is None:
        return None
    return {k: round(float(row[k]) * n, 1) for k in NUTRIENTS}

def meal_totals(items):
    """Add up a list of dishes. Returns the totals and the items that could not be counted."""
    totals = dict.fromkeys(NUTRIENTS, 0.0)
    skipped = []
    for item in items:
        n = nutrients(item["dish"], item["amount"], item["unit"])
        if n is None:
            skipped.append(f"{item['amount']} {item['unit']} {item['dish']}")
            continue
        for k in NUTRIENTS:
            totals[k] += n[k]
    return {k: round(v) for k, v in totals.items()}, skipped