"""Build nutrition_table.csv from recipes.json + ingredients.json + the USDA files.

    python build_nutrition.py

Needs the USDA SR Legacy and FNDDS CSV folders in usda_raw/ (not shipped; see
NOTICE.md for where to download them). Prints a check of our dishes against
USDA's own versions of the same dishes, where FNDDS has one.
"""
import csv, json
from pathlib import Path

HERE = Path(__file__).parent
RAW = HERE / "usda_raw"
SR = RAW / "FoodData_Central_sr_legacy_food_csv_2018-04" / "FoodData_Central_sr_legacy_food_csv_2018-04"
FNDDS = RAW / "FoodData_Central_survey_food_csv_2024-10-31" / "FoodData_Central_survey_food_csv_2024-10-31"
NUTRIENTS = {"1008": "kcal", "1003": "protein_g", "1005": "carbs_g", "1004": "fat_g", "1079": "fibre_g"}
ADDED_FAT = {"oil", "ghee", "butter"}  # scaled by the user's cooking style in the app
# FNDDS files store the older nutrient numbers in the same column
NUTRIENTS_FNDDS = {"208": "kcal", "203": "protein_g", "205": "carbs_g", "204": "fat_g", "291": "fibre_g"}
# Our dish -> the FNDDS description of USDA's version, for the sanity check
FNDDS_CHECK = {"dal": "Dal", "chicken curry": "Chicken curry", "mixed veg curry": "Vegetable curry",
               "veg biryani": "Biryani with vegetables", "phirni": "Firni", "sambar": "Sambar",
               "palak paneer": "Palak Paneer", "samosa": "Samosa", "idli": "Idli", "plain dosa": "Dosa",
               "onion pakoda": "Pakora", "chicken biryani": "Biryani with chicken", "fish curry": "Fish curry",
               "barfi": "Barfi or Burfi"}


def per_100g(folder, fdc_ids, codes=NUTRIENTS):
    """{fdc_id: {nutrient: value per 100 g}} for the given foods."""
    out = {i: {} for i in fdc_ids}
    with open(folder / "food_nutrient.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["fdc_id"] in out and row["nutrient_id"] in codes:
                out[row["fdc_id"]][codes[row["nutrient_id"]]] = float(row["amount"])
    return out


def main():
    ingredients = json.loads((HERE / "ingredients.json").read_text(encoding="utf-8"))["ingredients"]
    recipes = json.loads((HERE / "recipes.json").read_text(encoding="utf-8"))["dishes"]

    sr_ids = {str(v["fdc_id"]) for v in ingredients.values() if v.get("source") != "fndds"}
    fndds_ids = {str(v["fdc_id"]) for v in ingredients.values() if v.get("source") == "fndds"}
    usda = {**per_100g(SR, sr_ids), **per_100g(FNDDS, fndds_ids, NUTRIENTS_FNDDS)}
    for key, v in ingredients.items():
        missing = set(NUTRIENTS.values()) - set(usda[str(v["fdc_id"])])
        if missing:
            print(f"warning: {key} (fdc {v['fdc_id']}) has no {', '.join(sorted(missing))}; counted as 0")

    def nutrients(parts):
        """Totals for {ingredient: grams}, plus the share from added fat (oil, ghee, butter)."""
        total = dict.fromkeys(NUTRIENTS.values(), 0.0)
        added = {"added_fat_kcal": 0.0, "added_fat_g": 0.0}
        for ing, grams in parts.items():
            n = usda[str(ingredients[ing]["fdc_id"])]
            for k in total:
                total[k] += n.get(k, 0.0) * grams / 100
            if ing in ADDED_FAT:
                added["added_fat_kcal"] += n.get("kcal", 0.0) * grams / 100
                added["added_fat_g"] += n.get("fat_g", 0.0) * grams / 100
        return {k: round(v, 1) for k, v in {**total, **added}.items()}

    rows, options = [], []
    for dish, r in recipes.items():
        rows.append({"dish": dish, "unit": r["unit"], "grams_per_unit": r["grams"],
                     "default_amount": r["default"], **nutrients(r["ingredients"])})
        for name, parts in r.get("options", {}).items():
            options.append({"dish": dish, "option": name, **nutrients(parts)})

    for name, data in (("nutrition_table.csv", rows), ("nutrition_options.csv", options)):
        with open(HERE / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0]))
            w.writeheader()
            w.writerows(data)
    print(f"Wrote nutrition_table.csv ({len(rows)} dishes, per unit) and "
          f"nutrition_options.csv ({len(options)} add-ons)\n")

    # Sanity check against USDA's own (American-style) versions, per 100 g
    names = {}
    with open(FNDDS / "food.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for ours, theirs in FNDDS_CHECK.items():
                if row["description"].split(",")[0].strip() == theirs and ours not in names:
                    names[ours] = (row["fdc_id"], row["description"])
    theirs = per_100g(FNDDS, {i for i, _ in names.values()}, NUTRIENTS_FNDDS)
    print(f"{'per 100 g':22} {'ours kcal':>9} {'USDA kcal':>9}   {'ours prot':>9} {'USDA prot':>9}   USDA food")
    by_dish = {r["dish"]: r for r in rows}
    for ours, (fid, desc) in names.items():
        if ours not in by_dish:
            continue
        r = by_dish[ours]
        k = 100 / r["grams_per_unit"]
        t = theirs[fid]
        print(f"{ours:22} {r['kcal'] * k:9.0f} {t.get('kcal', 0):9.0f}   {r['protein_g'] * k:9.1f} {t.get('protein_g', 0):9.1f}   {desc[:45]}")


if __name__ == "__main__":
    main()
