export interface CategoryOption {
  id: string;
  label: string;
  image: string;
}

export const PRODUCT_CATEGORIES: CategoryOption[] = [
  {
    id: "lithium_battery",
    label: "Lithium Battery",
    image: "/uploads/products/Lithium Battery.jpeg",
  },
  {
    id: "lead_acid_battery",
    label: "Lead Acid Battery",
    image: "/uploads/products/LeadAcidBattery.jpeg",
  },
  {
    id: "inverter",
    label: "Inverter",
    image: "/uploads/products/inverter.png",
  },
  {
    id: "lithium_inverter_combo",
    label: "Lithium Battery + Inverter combo",
    image: "/uploads/products/Lithiuminvertercombo.jpeg",
  },
  {
    id: "lead_acid_inverter_combo",
    label: "Lead Acid Battery + Inverter combo",
    image: "/uploads/products/leadinvertercombo.png",
  },
];

export function getProductCategoryImage(
  category?: string | null,
  customImageUrl?: string | null
): string {
  if (customImageUrl && customImageUrl.trim()) {
    return customImageUrl.trim();
  }
  if (!category) return "/uploads/products/inverter.png";

  const cat = category.toLowerCase().trim();
  const matched = PRODUCT_CATEGORIES.find(
    (c) => c.id === cat || c.label.toLowerCase() === cat
  );

  return matched ? matched.image : "/uploads/products/inverter.png";
}

export function getProductCategoryLabel(category?: string | null): string {
  if (!category) return "General";
  const cat = category.toLowerCase().trim();
  const matched = PRODUCT_CATEGORIES.find(
    (c) => c.id === cat || c.label.toLowerCase() === cat
  );
  return matched ? matched.label : category;
}
