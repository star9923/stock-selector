#!/usr/bin/env python3
"""
快速测试 AI 连接
"""
from anthropic import Anthropic
import sys


def test_connection(base_url, api_key, model):
    """测试连接"""
    print(f"\n{'='*60}")
    print(f"测试配置:")
    print(f"  Base URL: {base_url}")
    print(f"  API Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"  模型: {model}")
    print('='*60)

    try:
        client = Anthropic(api_key=api_key, base_url=base_url)
        print("\n✓ 客户端创建成功")

        print("\n发送测试请求...")
        response = client.messages.create(
            model=model,
            max_tokens=50,
            messages=[{"role": "user", "content": "回复OK两个字"}],
        )

        reply = response.content[0].text
        print(f"✓ 连接成功!")
        print(f"  响应: {reply}")
        return True

    except Exception as e:
        print(f"\n✗ 连接失败:")
        print(f"  错误: {str(e)[:200]}")
        return False


if __name__ == "__main__":
    from services.ai_analyzer import load_ai_config

    config = load_ai_config()

    # 测试当前配置
    print("\n【测试 1】当前配置")
    test_connection(
        config.get("base_url"),
        config.get("api_key"),
        config.get("model"),
    )

    # 测试其他可能的 Base URL
    print("\n\n【测试 2】尝试其他 Base URL")
    test_urls = [
        "https://agentrouter.org/v1",
        "https://api.agentrouter.org",
        "https://agentrouter.org",
    ]

    for url in test_urls:
        if url != config.get("base_url"):
            success = test_connection(url, config.get("api_key"), config.get("model"))
            if success:
                print(f"\n✓ 找到可用的 Base URL: {url}")
                print(f"  请在设置中更新为此 URL")
                break

    print("\n\n如果所有测试都失败，请:")
    print("1. 检查 API Key 是否有效")
    print("2. 查看 agentrouter.org 官方文档")
    print("3. 联系支持: https://discord.com/invite/V6kaP6Rg44")
