"""
获取并保存股票代码和名称映射
"""
import akshare as ak
import json
import os

print("Fetching stock list...")

try:
    df = ak.stock_info_a_code_name()
    df.columns = ["code", "name"]

    print(f"Fetched {len(df)} stocks")

    stock_dict = dict(zip(df["code"], df["name"]))

    json_file = "stock_mapping.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(stock_dict, f, ensure_ascii=False, indent=2)

    print(f"Saved to {json_file}")

    csv_file = "stock_mapping.csv"
    df.to_csv(csv_file, index=False, encoding="utf-8-sig")
    print(f"Saved to {csv_file}")

    print(f"\n=== Statistics ===")
    print(f"   Total: {len(df)}")
    print(f"   ST: {len(df[df['name'].str.contains('ST', na=False)])}")
    print(f"   Delisted: {len(df[df['name'].str.contains('退', na=False)])}")

    print(f"\nFirst 10 records:")
    print(df.head(10).to_string(index=False))

except Exception as e:
    print(f"[ERROR] {e}")
