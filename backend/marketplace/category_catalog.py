"""Built-in marketplace categories and compatibility names for older records."""
BUILTIN_CATEGORIES = (
    ("Books", "Book"), ("Electronics", "Tech"), ("Clothing", "Wear"),
    ("Furniture", "Home"), ("Footwear", "Shoes"),
    ("Study Supplies", "Study"), ("Sports & Fitness", "Sport"),
    ("Personal Care", "Care"), ("Other", "More"),
)
DEFAULT_CATEGORY_NAMES = {name.casefold() for name, _ in BUILTIN_CATEGORIES}


def canonical_category_name(value):
    name = str(value or "").strip()
    if name.casefold() == "footwares":
        return "Footwear"
    return next((label for label, _ in BUILTIN_CATEGORIES if label.casefold() == name.casefold()), name)


def builtin_category_options():
    return [
        {"id": f"builtin-{index}", "name": name, "icon": icon, "image": None, "created_at": None, "built_in": True}
        for index, (name, icon) in enumerate(BUILTIN_CATEGORIES, 1)
    ]
