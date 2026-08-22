import pandas as pd
import json

print("=== CSV Analysis ===")
df = pd.read_csv('data/processed/output_200.csv')
print(f"Total rows: {len(df)}")
print(f"Columns: {len(df.columns)}")
print("Sample Columns populated:")
non_empty = df.notna().sum()
print(non_empty[non_empty > 0].head(10))

print("\n=== JSON Analysis ===")
with open('data/processed/products_200.json', encoding='utf-8') as f:
    products = json.load(f)

mfg_conf = [p.get('manufacturer_confidence', 0) for p in products if p.get('manufacturer_confidence') is not None]
cls_conf = [p.get('classification_confidence', 0) for p in products if p.get('classification_confidence') is not None]

print(f"Total JSON products: {len(products)}")
if mfg_conf: print(f"Avg Mfg Conf: {sum(mfg_conf)/len(mfg_conf):.2f}")
if cls_conf: print(f"Avg Class Conf: {sum(cls_conf)/len(cls_conf):.2f}")

attrs = [len(p.get('attributes', [])) for p in products]
print(f"Avg extracted attributes per product: {sum(attrs)/len(attrs):.2f}")
