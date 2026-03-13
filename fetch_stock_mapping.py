"""
获取并保存股票代码和名称映射
"""
import akshare as ak
import json
import os

print("正在获取股票列表...")

try:
    # 获取A股股票列表
    df = ak.stock_info_a_code_name()
    df.columns = ["code", "name"]

    print(f"成功获取 {len(df)} 只股票")

    # 保存为JSON格式
    stock_dict = dict(zip(df["code"], df["name"]))

    json_file = "stock_mapping.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(stock_dict, f, ensure_ascii=False, indent=2)

    print(f"✅ 已保存到 {json_file}")

    # 保存为CSV格式
    csv_file = "stock_mapping.csv"
    df.to_csv(csv_file, index=False, encoding="utf-8-sig")
    print(f"✅ 已保存到 {csv_file}")

    # 显示统计信息
    print(f"\n📊 统计信息:")
    print(f"   总股票数: {len(df)}")
    print(f"   ST股票数: {len(df[df['name'].str.contains('ST', na=False)])}")
    print(f"   退市股票数: {len(df[df['name'].str.contains('退', na=False)])}")

    # 显示前10条
    print(f"\n前10条数据:")
    print(df.head(10).to_string(index=False))

except Exception as e:
    print(f"❌ 获取失败: {e}")
