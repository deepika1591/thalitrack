import sys
import vision
import nutrition

saved = vision.read_photo(sys.argv[1])
items, problems = vision.validate(saved["reading"])

for item in items:
    n = nutrition.nutrients(item["dish"], item["amount"], item["unit"])
    kcal = f"{n['kcal']:.0f} kcal" if n else "not counted"
    print(f"{item['dish']:24} {item['amount']:>4} {item['unit']:7} {kcal}")

totals, skipped = nutrition.meal_totals(items)
print()
print(f"This meal: {totals['kcal']} kcal | protein {totals['protein_g']} g | "
      f"carbs {totals['carbs_g']} g | fat {totals['fat_g']} g | fibre {totals['fibre_g']} g")
for s in skipped:
    print("Not counted:", s)