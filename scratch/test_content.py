# -*- coding: utf-8 -*-
from src.content import generate_content

product = {
    "brand_name": "FRIGIDAIRE\u00ae",
    "product_name": "Dishwasher",
    "With": "CleanBoost\u2122",
    "attributes": [],
}
out = generate_content(product)
print(repr(out["descriptions"]["SHORT_DESC"]))
print(repr(out["descriptions"]["MARKETING_DESCRIPTION"]))