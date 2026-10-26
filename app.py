"""The web app: upload a photo, confirm, save, see your day."""
import hashlib
from pathlib import Path

import streamlit as st

import db
import learn
import screens
import vision

st.set_page_config(page_title="ThaliTrack")
st.title("ThaliTrack")
st.caption("Nutrition from USDA FoodData Central, built into Indian dishes. "
           "Estimates only, not medical or dietary advice.")

if "db" not in st.session_state:
    st.session_state.db = db.connect()
    st.session_state.user = None

if st.session_state.user is None:
    screens.login_screen()
    st.stop()

st.write(f"Logged in as {st.session_state.user.email}")
upload = st.file_uploader("Photo of your meal, from above (jpg)", type=["jpg", "jpeg"])
if upload:
    photo = hashlib.sha1(upload.getvalue()).hexdigest()[:16]
    path = Path("uploads") / f"{photo}.jpg"
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(upload.getvalue())
    try:
        with st.spinner("Reading your plate..."):
            saved = vision.read_photo(path)
    except Exception as e:
        st.error(f"Gemini could not read this photo: {e}")
        st.stop()
    items, problems = vision.validate(saved["reading"])
    items = learn.personalise(items, st.session_state.db)
    st.image(upload.getvalue(), width=320)
    screens.log_meal(items, photo)

screens.show_today()
screens.style_setting()
again, key = screens.log_again()
if again:
    screens.log_meal(again, key)
screens.show_progress()

st.sidebar.caption("Photos use this app's free Gemini quota, about 20 a day shared by everyone. "
                   "'Log a meal again' uses none.")