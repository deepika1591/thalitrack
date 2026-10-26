"""Save meals and corrections in Supabase."""
import os

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()


def connect():
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def sign_up(db, email, password):
    return db.auth.sign_up({"email": email, "password": password}).user


def sign_in(db, email, password):
    return db.auth.sign_in_with_password({"email": email, "password": password}).user


def save_meal(db, items, photo, where_eaten):
    """Save one meal and its dishes. The database fills in who and when."""
    meal = db.table("meals").insert({"photo": photo, "where_eaten": where_eaten}).execute().data[0]
    rows = [{"meal_id": meal["id"],
             "dish": item["dish"],
             "amount": item["amount"],
             "unit": item["unit"],
             "model_dish": item.get("model_dish"),
             "confidence": item.get("confidence")} for item in items]
    db.table("meal_items").insert(rows).execute()
    return meal["id"]


def meals_since(db, since):
    """This user's meals since a moment in time, each with its dishes, oldest first."""
    return (db.table("meals").select("*, meal_items(*)")
            .gte("eaten_at", since.isoformat()).order("eaten_at").execute().data)

def get_style(db):
    """This person's cooking style, kept on their account. 'normal' until they choose."""
    return (db.auth.get_user().user.user_metadata or {}).get("style", "normal")


def set_style(db, style):
    db.auth.update_user({"data": {"style": style}})
