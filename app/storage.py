import json
import os
from typing import Any

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

SELLERS_FILE = f"{DATA_DIR}/sellers.json"
APPLICATIONS_FILE = f"{DATA_DIR}/applications.json"
PRODUCTS_FILE = f"{DATA_DIR}/products.json"


def _read(path: str) -> Any:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write(path: str, data: Any):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# --- Applications ---
def get_applications() -> dict:
    return _read(APPLICATIONS_FILE)

def save_application(user_id: int, data: dict):
    apps = get_applications()
    apps[str(user_id)] = data
    _write(APPLICATIONS_FILE, apps)

def get_application(user_id: int) -> dict | None:
    return get_applications().get(str(user_id))

def update_application_status(user_id: int, status: str):
    apps = get_applications()
    if str(user_id) in apps:
        apps[str(user_id)]["status"] = status
        _write(APPLICATIONS_FILE, apps)


# --- Sellers ---
def get_sellers() -> dict:
    return _read(SELLERS_FILE)

def add_seller(user_id: int, data: dict):
    sellers = get_sellers()
    sellers[str(user_id)] = data
    _write(SELLERS_FILE, sellers)

def is_seller(user_id: int) -> bool:
    return str(user_id) in get_sellers()

def get_seller(user_id: int) -> dict | None:
    return get_sellers().get(str(user_id))


# --- Products ---
def get_all_products() -> list:
    data = _read(PRODUCTS_FILE)
    return data if isinstance(data, list) else []

def get_seller_products(seller_id: int) -> list:
    return [p for p in get_all_products() if p.get("seller_id") == seller_id]

def add_product(product: dict):
    products = get_all_products()
    product["id"] = len(products) + 1
    products.append(product)
    _write(PRODUCTS_FILE, products)

def delete_product(product_id: int, seller_id: int) -> bool:
    products = get_all_products()
    new = [p for p in products if not (p["id"] == product_id and p["seller_id"] == seller_id)]
    if len(new) < len(products):
        _write(PRODUCTS_FILE, new)
        return True
    return False
