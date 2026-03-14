#!/usr/bin/env python3
"""
update_board_cache.py - 手动更新板块数据缓存
当API可用时运行此脚本，将实时数据保存到本地缓存
"""
import sys
from sentiment import get_board_sentiment
from sector_data_fallback import save_board_data_to_fallback, save_sector_stocks_cache
from sector_analyzer import get_sector_stocks


def update_board_sentiment():
    """更新板块情绪数据"""
    print("=" * 60)
    print("板块情绪数据缓存更新")
    print("=" * 60)
    print()

    print("正在获取实时板块数据...")
    df = get_board_sentiment()

    if df.empty:
        print("❌ 获取失败，无法更新缓存")
        print("   可能原因：")
        print("   1. 网络连接问题")
        print("   2. API服务不可用")
        print("   3. 当前非交易时间")
        return False

    # 添加 total_count 列
    df['total_count'] = df['up_count'] + df['down_count']

    print(f"✅ 成功获取 {len(df)} 个板块数据")
    print()
    print("前5个板块预览：")
    print(df.head())
    print()

    # 保存到备用缓存
    save_board_data_to_fallback(df)
    return True


def update_sector_stocks(sector_names: list):
    """更新指定板块的成分股数据"""
    print()
    print("=" * 60)
    print("板块成分股数据缓存更新")
    print("=" * 60)
    print()

    success_count = 0
    fail_count = 0

    for sector_name in sector_names:
        print(f"正在获取 {sector_name} 成分股...")
        try:
            df = get_sector_stocks(sector_name)
            if not df.empty:
                save_sector_stocks_cache(sector_name, df)
                print(f"✅ {sector_name}: {len(df)} 只股票")
                success_count += 1
            else:
                print(f"❌ {sector_name}: 获取失败")
                fail_count += 1
        except Exception as e:
            print(f"❌ {sector_name}: {str(e)[:50]}")
            fail_count += 1

    print()
    print(f"更新完成: 成功 {success_count} 个，失败 {fail_count} 个")
    return success_count > 0


def main():
    print("=" * 60)
    print("板块数据缓存更新工具")
    print("=" * 60)
    print()

    # 1. 更新板块情绪数据
    board_success = update_board_sentiment()

    # 2. 更新热门板块的成分股数据
    if board_success:
        print()
        response = input("是否更新热门板块成分股数据？(y/n): ").strip().lower()
        if response == 'y':
            # 更新前10个热门板块
            hot_sectors = ["人工智能", "半导体", "新能源汽车", "光伏", "锂电池",
                          "5G", "医药", "白酒", "军工", "消费电子"]
            update_sector_stocks(hot_sectors)

    print()
    print("=" * 60)
    if board_success:
        print("✅ 缓存更新完成！")
    else:
        print("⚠️  部分更新失败，请检查网络连接")
    print("=" * 60)

    return 0 if board_success else 1


if __name__ == "__main__":
    sys.exit(main())
