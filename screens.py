"""The pieces of the web page: login, the confirm list, totals and today's meals."""
from datetime import datetime

import streamlit as st

import db
import learn
import vision


def login_screen():
    with st.form("login"):
        email = st.text_input("Email")
        password = st.text_input("Password (at least 6 characters)", type="password")
        log_in, sign_up = st.columns(2)
        logging_in = log_in.form_submit_button("Log in", use_container_width=True)
        signing_up = sign_up.form_submit_button("Sign up", use_container_width=True)
    try:
        if logging_in:
            st.session_state.user = db.sign_in(st.session_state.db, email, password)
            st.rerun()
        if signing_up:
            st.session_state.user = db.sign_up(st.session_state.db, email, password)
            st.rerun()
    except Exception as e:
        st.error(f"That didn't work: {e}")


def confirm(items, key):
    """One row per dish: tap the right name, nudge the amount. Returns what the user confirmed."""
    st.subheader("Is this right?")
    confirmed = []
    for i, item in enumerate(items):
        row = f"{key}-{i}"
        choices = [item["dish"]] + item["alternatives"] + ["something else"]
        unsure = item["confidence"] < 0.85 or item["dish"] == "unknown"
        label = f"Dish {i + 1}" + (" - not sure, please check" if unsure else "")
        if item.get("habit"):
            label += f" - usually {item['dish']} for you"
        dish = st.segmented_control(label, choices, default=item["dish"], key=row + "dish") or item["dish"]
        if dish == "something else":
            dish = st.selectbox("Which dish?", vision.MENU, key=row + "other")
        amount = st.number_input(f"Amount ({item['unit']}) - 0 removes it", min_value=0.0, value=float(item["amount"]),
                                 step=0.5, key=row + "amount")
        if amount > 0 and dish != "unknown":
            confirmed.append({"dish": dish, "amount": amount, "unit": item["unit"],
                              "model_dish": item.get("model_said", item["dish"]),
                              "confidence": item["confidence"]})
    return confirmed


def show_totals(label, totals):
    kcal, protein, carbs, fat = st.columns(4)
    kcal.metric(label, f"{totals['kcal']} kcal")
    protein.metric("Protein", f"{totals['protein_g']} g")
    carbs.metric("Carbs", f"{totals['carbs_g']} g")
    fat.metric("Fat", f"{totals['fat_g']} g")


def log_meal(items, key):
    """Confirm the dishes, choose home or outside, see the totals, save."""
    confirmed = confirm(items, key)
    where = st.radio("Where did you eat?", ["home", "outside"], horizontal=True, key=key + "where")
    totals, skipped = learn.meal_totals(confirmed, where)
    show_totals("This meal", totals)
    if st.session_state.get("saved") == key:
        st.success("Saved. Upload another photo to log your next meal.")
    elif st.button("Save this meal", type="primary", key=key + "save"):
        db.save_meal(st.session_state.db, confirmed, key, where)
        st.session_state.saved = key
        st.rerun()


def show_today():
    midnight = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
    meals = db.meals_since(st.session_state.db, midnight)
    st.subheader("Today")
    if not meals:
        st.write("Nothing logged yet today.")
        return
    day = {"kcal": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0, "fibre_g": 0}
    for meal in meals:
        totals, _ = learn.meal_totals(meal["meal_items"], meal["where_eaten"])
        time = datetime.fromisoformat(meal["eaten_at"]).astimezone().strftime("%H:%M")
        dishes = ", ".join(item["dish"] for item in meal["meal_items"])
        st.write(f"**{time}** | {dishes} | {totals['kcal']} kcal")
        for k in day:
            day[k] += totals[k]
    show_totals("Today", day)
def style_setting():
    """In the sidebar: how much oil and ghee this person cooks with at home. Saved to their account."""
    learn.style()
    st.sidebar.radio("How do you cook at home?", list(learn.STYLES), key="style",
                     on_change=lambda: db.set_style(st.session_state.db, st.session_state.style),
                     help="Scales the oil and ghee in tadka and sabzi. Meals eaten outside always count as rich.")

def log_again():
    """Pick a recent meal to log again. Returns its dishes and a key, or (None, None)."""
    st.subheader("Log a meal again")
    meals = learn.recent(st.session_state.db)
    if not meals:
        st.write("Meals you save will appear here, ready to log again without a photo.")
        return None, None
    labels = ["Choose a recent meal..."] + [label for label, _, _ in meals]
    pick = st.selectbox("Same as before? Pick it, adjust anything, save.", labels, key="again")
    if pick == labels[0]:
        return None, None
    label, meal_id, items = meals[labels.index(pick) - 1]
    return items, f"again-{meal_id}"

def show_progress():
    st.subheader("Your last two weeks")
    days = learn.daily(st.session_state.db)
    if days.empty:
        st.write("Charts appear here once you have saved a few meals.")
        return
    st.write("Calories per day")
    st.bar_chart(days, x="day", y="kcal")
    st.write("Dish corrections per photo meal: this line falling means the app is learning your kitchen")
    st.line_chart(days, x="day", y="corrections per photo meal")
    share = learn.repeat_share(st.session_state.db)
    if share is not None:
        st.metric("Dishes this week you had logged before", f"{share}%")
