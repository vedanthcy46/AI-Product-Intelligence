# -*- coding: utf-8 -*-
"""Full end-to-end orchestrator test with a synthetic master + row (offline)."""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pandas as pd

from src.pipeline.orchestrator import PipelineOrchestrator
from src.pipeline.batch import process_batch

master_df = pd.DataFrame({
    "Manufacturer_Name": ["Rheem Manufacturing", "Whirlpool Corporation"],
    "Manufacturer_Code": ["RHEEM", "WHRPL"],
    "Brand_Name": ["FRIGIDAIRE\u00ae", "Whirlpool\u00ae"],
    "Brand_Code": ["FRIG", "WHIR"],
})
master_path = os.path.join(tempfile.gettempdir(), "unihack_master_test.xlsx")
master_df.to_excel(master_path, index=False)

rows = pd.DataFrame([{
    "Mfg_Part_Num": "PDSH4816AF",
    "Part_Desc": "PDSH4816AF Dishwasher SS - Display Only",
    "E1_Brand": "-- Unbranded --",
    "Unilog_Brand": "-- No Unilog Brand --",
    "DIB_Brand": "-- No DIB Brand --",
    "Part_Manuf": "Appliance Dealers Cooperative (APPDE)",
}, {
    "Mfg_Part_Num": "WDT750SAHZ",
    "Part_Desc": "Whirlpool Dishwasher 3rd Rack",
    "E1_Brand": "Whirlpool",
    "Unilog_Brand": "Whirlpool",
    "DIB_Brand": "Whirlpool",
    "Part_Manuf": "Whirlpool Corporation",
}])

orch = PipelineOrchestrator(master_path)
internal = orch.build_internal_product(rows.iloc[0].to_dict(), row_id="0")
print("INTERNAL:")
print("  manufacturer:", internal.get("manufacturer_name"))
print("  brand:", internal.get("brand_name"))
print("  classpath:", internal.get("classpath"))
print("  attrs:", [(a["label"], a["value"], a.get("uom")) for a in internal.get("attributes", [])])
print("  confidence:", internal.get("confidence", {}).get("status"), internal.get("needs_review"))
print("  invoice:", internal.get("descriptions", {}).get("INVOICE_DESC"))
print("  retail:", internal.get("descriptions", {}).get("RETAIL_DESC"))

out_path = os.path.join(tempfile.gettempdir(), "unihack_batch_test.csv")
json_path = os.path.join(tempfile.gettempdir(), "unihack_internal_test.json")
df = process_batch(rows, master_path=master_path, output_path=out_path,
                   internal_json_path=json_path, limit=None)
print("\nBATCH: %d rows, %d cols" % df.shape)
print("  cols match 252:", df.shape[1] == 252 if os.path.exists(out_path) else "n/a")
print("  header[0:3]:", list(df.columns[:3]))
print("\nOK")