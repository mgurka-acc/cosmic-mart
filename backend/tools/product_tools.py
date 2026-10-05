import json
from pathlib import Path
from sqlmodel import Session, select
from backend.models import Inventory

PRODUCTS_FILE = Path(__file__).parent.parent / "data" / "products.json"

def _load_products():
    with open(PRODUCTS_FILE) as f:
        return json.load(f)

def search_product_catalog(query: str, market: str, session: Session) -> dict:
    """Search product catalog and return stock + price info."""
    products = _load_products()
    query_lower = query.lower()
    matches = [
        p for p in products
        if query_lower in p["name"].lower() or query_lower in p["description"].lower() or query_lower in p["category"].lower()
    ]
    if not matches:
        return {"found": False, "message": f"No products found matching '{query}'"}

    results = []
    for product in matches[:5]:
        inv = session.exec(
            select(Inventory).where(
                Inventory.product_id == product["id"],
                Inventory.market == market
            )
        ).first()
        stock_info = {}
        if inv:
            stock_info = {
                "current_stock": inv.current_stock,
                "days_of_supply": round(inv.days_of_supply, 1),
                "available": inv.current_stock > 0
            }
        else:
            stock_info = {"current_stock": 0, "days_of_supply": 0, "available": False}
        results.append({**product, **stock_info, "market": market})
    return {"found": True, "products": results}


PRODUCT_TOOL_DEF = {
    "name": "search_product_catalog",
    "description": "Search the product catalog for items matching a query. Returns product details including current stock level and price for the specified market.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search term (product name, category, or keyword)"},
            "market": {"type": "string", "description": "Market ID (e.g. UK, US, JP)"}
        },
        "required": ["query", "market"]
    }
}
