#!/usr/bin/env python3
"""
diagnose_api.py - API 连接诊断工具
"""
import sys
from datetime import datetime
import akshare_config
import akshare as ak


def check_time():
    """检查当前时间"""
    now = datetime.now()
    is_weekday = now.weekday() < 5
    is_trading_hour = 9 <= now.hour < 15

    print("=" * 60)
    print("时间检查")
    print("=" * 60)
    print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S %A')}")
    print(f"是否工作日: {'✅ 是' if is_weekday else '❌ 否（周末）'}")
    print(f"是否交易时间: {'✅ 是 (9:30-15:00)' if is_trading_hour else '❌ 否'}")

    if not is_weekday:
        print("\n⚠️  当前是周末，API 可能不稳定")
    elif not is_trading_hour:
        print("\n⚠️  当前非交易时间，API 可能不稳定")
    else:
        print("\n✅ 当前是交易时间，API 应该可用")

    return is_weekday and is_trading_hour


def check_network():
    """检查网络连接"""
    print("\n" + "=" * 60)
    print("网络检查")
    print("=" * 60)

    import socket

    # 检查 DNS
    try:
        ip = socket.gethostbyname('push2.eastmoney.com')
        print(f"✅ DNS 解析成功: push2.eastmoney.com -> {ip}")
    except Exception as e:
        print(f"❌ DNS 解析失败: {e}")
        return False

    # 检查连接
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((ip, 443))
        sock.close()

        if result == 0:
            print(f"✅ 端口 443 可连接")
            return True
        else:
            print(f"❌ 端口 443 不可连接")
            return False
    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        return False


def check_api():
    """检查 API 可用性"""
    print("\n" + "=" * 60)
    print("API 测试")
    print("=" * 60)

    tests = [
        ("股票列表", lambda: ak.stock_info_a_code_name()),
        ("单只股票历史", lambda: ak.stock_zh_a_hist(
            symbol='000001', period='daily',
            start_date='20260301', end_date='20260314', adjust=''
        )),
        ("板块数据", lambda: ak.stock_board_industry_spot_em()),
    ]

    results = []
    for name, func in tests:
        print(f"\n测试: {name}")
        try:
            import socket
            socket.setdefaulttimeout(10)
            df = func()
            print(f"  ✅ 成功: {len(df)} 条记录")
            results.append(True)
        except Exception as e:
            print(f"  ❌ 失败: {type(e).__name__}")
            print(f"     {str(e)[:80]}")
            results.append(False)

    return all(results)


def check_cache():
    """检查缓存状态"""
    print("\n" + "=" * 60)
    print("缓存检查")
    print("=" * 60)

    import os
    import json

    cache_dir = '.cache'
    if not os.path.exists(cache_dir):
        print("❌ 缓存目录不存在")
        return

    # 检查板块缓存
    board_cache = os.path.join(cache_dir, 'board_sentiment_fallback.json')
    if os.path.exists(board_cache):
        with open(board_cache, 'r') as f:
            data = json.load(f)
        print(f"✅ 板块缓存: {len(data['data'])} 个板块")
        print(f"   更新时间: {data['timestamp']}")
    else:
        print("❌ 板块缓存不存在")

    # 检查成分股缓存
    sector_dir = os.path.join(cache_dir, 'sector_stocks')
    if os.path.exists(sector_dir):
        count = len([f for f in os.listdir(sector_dir) if f.endswith('.json')])
        print(f"✅ 成分股缓存: {count} 个板块")
    else:
        print("❌ 成分股缓存不存在")

    # 检查个股缓存
    stock_dir = os.path.join(cache_dir, 'stock_history')
    if os.path.exists(stock_dir):
        count = len([f for f in os.listdir(stock_dir) if f.endswith('.json')])
        print(f"✅ 个股缓存: {count} 只股票")
    else:
        print("❌ 个股缓存不存在")


def main():
    print("\n" + "=" * 60)
    print("A股选股系统 - API 连接诊断")
    print("=" * 60)

    # 1. 时间检查
    is_trading_time = check_time()

    # 2. 网络检查
    network_ok = check_network()

    # 3. API 测试
    api_ok = check_api()

    # 4. 缓存检查
    check_cache()

    # 总结
    print("\n" + "=" * 60)
    print("诊断总结")
    print("=" * 60)

    if api_ok:
        print("✅ API 连接正常，可以正常使用")
    elif not is_trading_time:
        print("⚠️  当前非交易时间，建议：")
        print("   1. 在交易时间（周一至周五 9:30-15:00）重试")
        print("   2. 使用缓存数据")
        print("   3. 运行 update_board_cache.py 更新缓存")
    elif not network_ok:
        print("❌ 网络连接问题，建议：")
        print("   1. 检查网络连接")
        print("   2. 检查防火墙设置")
        print("   3. 尝试使用 VPN")
    else:
        print("❌ API 服务不可用，建议：")
        print("   1. 稍后重试")
        print("   2. 使用缓存数据")
        print("   3. 检查 akshare 版本是否最新")

    print("=" * 60)

    return 0 if api_ok else 1


if __name__ == "__main__":
    sys.exit(main())
