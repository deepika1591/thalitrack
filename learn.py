"""Learn each user's usual dishes, amounts and cooking style from their own meals."""
import statistics
from collections import Counter
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

import db
import nutrition

STYLES = {"light": 0.5, "normal": 1.0, "rich": 1.5}


def history(database, days=60):
    """Every dish this person has saved in the last `days` days."""
    since = datetime.now().astimezone() - timedelta(days=days)
    return [item for meal in db.meals_since(database, since) for item in meal["meal_items"]]

def habit(model_dish, past):
    """What this person usually picks when the model says `model_dish`: at least 2 times, and more than half."""
    picks = Counter(i["dish"] for i in past if i.get("model_dish") == model_dish)
    if not picks:
        return None
    dish, n = picks.most_common(1)[0]
    return dish if n >= 2 and n > sum(picks.values()) / 2 else None

def usual_amount(dish, unit, past):
    """This person's usual amount of a dish, once they have saved it at least twice in that unit."""
    amounts = [i["amount"] for i in past if i["dish"] == dish and i["unit"] == unit]
    return statistics.median(amounts) if len(amounts) >= 2 else None

def personalise(items, database):
    """Put this person's usual dish first, and fill in their usual amount for bowls and rice."""
    past = history(database)
    for item in items:
        usual = habit(item["dish"], past)
        if usual and usual != item["dish"]:
            item["model_said"] = item.get("model_said", item["dish"])
            item["alternatives"] = [item["dish"]] + [a for a in item["alternatives"] if a != usual]
            item["dish"] = usual
            item["habit"] = True
        if item["unit"] != "piece":
            amount = usual_amount(item["dish"], item["unit"], past)
            if amount:
                item["amount"] = amount
    return items

def style():
    """This person's cooking style, read from their account once per visit."""
    if "style" not in st.session_state:
        st.session_state.style = db.get_style(st.session_state.db)
    return st.session_state.style


def meal_totals(items, where_eaten):
    """Meal totals with tadka oil and ghee scaled: by the person's style at home, as rich when eaten outside."""
    factor = STYLES["rich"] if where_eaten == "outside" else STYLES[style()]
    totals, skipped = nutrition.meal_totals(items)
    extra_kcal = extra_fat = 0.0
    for item in items:
        row = nutrition.TABLE.get(item["dish"])
        n = nutrition.units_of(row["unit"], item["amount"], item["unit"]) if row else None
        if n:
            extra_kcal += float(row["added_fat_kcal"]) * n * (factor - 1)
            extra_fat += float(row["added_fat_g"]) * n * (factor - 1)
    totals["kcal"] = round(totals["kcal"] + extra_kcal)
    totals["fat_g"] = round(totals["fat_g"] + extra_fat)
    return totals, skipped
def recent(database, days=14):
    """Recent meals to log again, newest first, one per different set of dishes."""
    since = datetime.now().astimezone() - timedelta(days=days)
    seen, meals = set(), []
    for meal in reversed(db.meals_since(database, since)):
        dishes = tuple(sorted(i["dish"] for i in meal["meal_items"]))
        if dishes in seen:
            continue
        seen.add(dishes)
        when = datetime.fromisoformat(meal["eaten_at"]).astimezone().strftime("%a %d %b, %H:%M")
        items = [{"dish": i["dish"], "alternatives": [], "amount": i["amount"], "unit": i["unit"],
                  "confidence": 1.0, "model_said": None} for i in meal["meal_items"]]
        meals.append((f"{when} | {', '.join(dishes)}", meal["id"], items))
    return meals

def daily(database, days=14):
    """One row per day: calories, and dish corrections per meal logged from a photo."""
    since = datetime.now().astimezone() - timedelta(days=days)
    rows = []
    for meal in db.meals_since(database, since):
        from_photo = not meal["photo"].startswith("again-")
        fixes = sum(1 for i in meal["meal_items"] if i.get("model_dish") and i["dish"] != i["model_dish"])
        rows.append({"day": datetime.fromisoformat(meal["eaten_at"]).astimezone().date(),
                     "kcal": meal_totals(meal["meal_items"], meal["where_eaten"])[0]["kcal"],
                     "photo meals": int(from_photo),
                     "corrections": fixes if from_photo else 0})
    if not rows:
        return pd.DataFrame()
    days_df = pd.DataFrame(rows).groupby("day", as_index=False).sum()
    days_df["day"] = [d.strftime("%m/%d") for d in days_df["day"]]
    days_df["corrections per photo meal"] = (days_df["corrections"] / days_df["photo meals"]).where(days_df["photo meals"] > 0)
    return days_df


def repeat_share(database):
    """Share of the last 7 days' dishes that this person had logged before."""
    week_start = datetime.now().astimezone() - timedelta(days=7)
    seen, this_week = set(), []
    for meal in db.meals_since(database, week_start - timedelta(days=60)):
        dishes = [i["dish"] for i in meal["meal_items"]]
        if datetime.fromisoformat(meal["eaten_at"]) >= week_start:
            this_week += [d in seen for d in dishes]
        seen.update(dishes)
    return round(100 * sum(this_week) / len(this_week)) if this_week else None

# Streamlit's servers run on UTC; show and group meals by Indian time.
import os, time
os.environ["TZ"] = "Asia/Kolkata"
if hasattr(time, "tzset"):
    time.tzset()

"import learn, os; print(os.environ['TZ'])"