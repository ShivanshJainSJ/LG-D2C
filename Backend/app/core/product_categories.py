from enum import Enum
from typing import Optional, Dict, List

class ProductCategory(str, Enum):
    LITHIUM_BATTERY = "lithium_battery"
    LEAD_ACID_BATTERY = "lead_acid_battery"
    INVERTER = "inverter"
    LITHIUM_INVERTER_COMBO = "lithium_inverter_combo"
    LEAD_ACID_INVERTER_COMBO = "lead_acid_inverter_combo"

CATEGORY_DISPLAY_NAMES: Dict[str, str] = {
    ProductCategory.LITHIUM_BATTERY.value: "Lithium Battery",
    ProductCategory.LEAD_ACID_BATTERY.value: "Lead Acid Battery",
    ProductCategory.INVERTER.value: "Inverter",
    ProductCategory.LITHIUM_INVERTER_COMBO.value: "Lithium Battery + Inverter combo",
    ProductCategory.LEAD_ACID_INVERTER_COMBO.value: "Lead Acid Battery + Inverter combo",
}

CATEGORY_IMAGE_ASSETS: Dict[str, str] = {
    ProductCategory.LITHIUM_BATTERY.value: "/uploads/products/Lithium Battery.jpeg",
    ProductCategory.LEAD_ACID_BATTERY.value: "/uploads/products/LeadAcidBattery.jpeg",
    ProductCategory.INVERTER.value: "/uploads/products/inverter.png",
    ProductCategory.LITHIUM_INVERTER_COMBO.value: "/uploads/products/Lithiuminvertercombo.jpeg",
    ProductCategory.LEAD_ACID_INVERTER_COMBO.value: "/uploads/products/leadinvertercombo.png",
}

def normalize_category_key(raw_cat: Optional[str], strict: bool = False) -> Optional[str]:
    """
    Normalizes a category input string (whether identifier or display name)
    to one of the 5 canonical category keys.
    When strict=True, rejects any fuzzy/unsupported strings.
    Returns None if not a valid supported category.
    """
    if not raw_cat:
        return None
    val = raw_cat.strip()
    
    # 1. Direct match with enum values
    val_key = val.lower().replace(" ", "_").replace("-", "_")
    for cat in ProductCategory:
        if cat.value == val_key:
            return cat.value

    # 2. Match with display names (case-insensitive)
    val_clean = " ".join(val.lower().replace("-", " ").replace("_", " ").split())
    for cat_key, display in CATEGORY_DISPLAY_NAMES.items():
        if display.lower() == val_clean:
            return cat_key

    if strict:
        return None

    # 3. Flexible variations on the 5 supported categories (legacy/fuzzy)
    if "lithium" in val_clean and ("combo" in val_clean or "inverter" in val_clean):
        return ProductCategory.LITHIUM_INVERTER_COMBO.value
    if ("lead" in val_clean or "tubular" in val_clean) and ("combo" in val_clean or "inverter" in val_clean):
        return ProductCategory.LEAD_ACID_INVERTER_COMBO.value
    if "combo" in val_clean:
        return ProductCategory.LEAD_ACID_INVERTER_COMBO.value
    if "lithium" in val_clean:
        return ProductCategory.LITHIUM_BATTERY.value
    if "lead" in val_clean or "tubular" in val_clean or "battery" in val_clean:
        return ProductCategory.LEAD_ACID_BATTERY.value
    if "inverter" in val_clean:
        return ProductCategory.INVERTER.value

    return None

def get_category_image_url(category: Optional[str], custom_image_url: Optional[str] = None) -> str:
    """
    Returns the custom image if explicitly set; otherwise returns
    the official category image mapping.
    """
    if custom_image_url and custom_image_url.strip():
        return custom_image_url.strip()
    
    cat_key = normalize_category_key(category)
    if cat_key and cat_key in CATEGORY_IMAGE_ASSETS:
        return CATEGORY_IMAGE_ASSETS[cat_key]
    
    return "/uploads/products/inverter.png"

def get_category_display_name(category: Optional[str]) -> str:
    cat_key = normalize_category_key(category)
    if cat_key and cat_key in CATEGORY_DISPLAY_NAMES:
        return CATEGORY_DISPLAY_NAMES[cat_key]
    return category or "General"
