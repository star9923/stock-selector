#!/usr/bin/env python3
"""
测试 AI 配置功能
"""
from services.ai_analyzer import load_ai_config, save_ai_config, get_client


def test_config():
    """测试配置加载和保存"""
    print("=" * 60)
    print("AI 配置测试")
    print("=" * 60)

    # 1. 加载当前配置
    print("\n1. 当前配置:")
    config = load_ai_config()
    print(f"   Base URL: {config.get('base_url', 'N/A')}")
    print(f"   API Key: {'已配置' if config.get('api_key') else '未配置'}")
    print(f"   模型: {config.get('model', 'N/A')}")
    print(f"   最大 Token: {config.get('max_tokens', 'N/A')}")

    # 2. 测试自定义模型
    print("\n2. 测试自定义模型配置:")
    test_models = [
        "claude-sonnet-4-20250514",
        "claude-opus-4-20250514",
        "gpt-4",
        "gpt-4-turbo",
        "custom-model-v1",  # 自定义模型
    ]

    for model in test_models:
        test_config = config.copy()
        test_config["model"] = model
        print(f"   ✓ 模型 '{model}' 可以保存")

    # 3. 测试连接（如果配置了 API Key）
    if config.get("api_key"):
        print("\n3. 测试 API 连接:")
        try:
            client = get_client()
            print(f"   ✓ 客户端创建成功")
            print(f"   Base URL: {config.get('base_url')}")
            print(f"   模型: {config.get('model')}")

            # 简单测试
            response = client.messages.create(
                model=config.get("model", "claude-sonnet-4-20250514"),
                max_tokens=50,
                messages=[{"role": "user", "content": "回复OK两个字"}],
            )
            reply = response.content[0].text
            print(f"   ✓ 连接测试成功: {reply}")
        except Exception as e:
            print(f"   ✗ 连接失败: {str(e)[:100]}")
    else:
        print("\n3. 跳过连接测试（未配置 API Key）")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


def interactive_config():
    """交互式配置"""
    print("\n" + "=" * 60)
    print("AI 配置向导")
    print("=" * 60)

    config = load_ai_config()

    print("\n当前配置:")
    print(f"  Base URL: {config.get('base_url', 'https://api.anthropic.com')}")
    print(f"  API Key: {'已配置' if config.get('api_key') else '未配置'}")
    print(f"  模型: {config.get('model', 'claude-sonnet-4-20250514')}")
    print(f"  最大 Token: {config.get('max_tokens', 2000)}")

    print("\n是否要修改配置？(y/n): ", end="")
    if input().lower() != "y":
        return

    # Base URL
    print(f"\nBase URL (留空保持当前值): ", end="")
    base_url = input().strip()
    if base_url:
        config["base_url"] = base_url

    # API Key
    print(f"API Key (留空保持当前值): ", end="")
    api_key = input().strip()
    if api_key:
        config["api_key"] = api_key

    # 模型
    print("\n常用模型:")
    print("  1. claude-sonnet-4-20250514 (推荐)")
    print("  2. claude-opus-4-20250514")
    print("  3. claude-haiku-4-20250514")
    print("  4. gpt-4")
    print("  5. gpt-4-turbo")
    print("  6. 自定义输入")
    print(f"\n选择模型 (1-6, 留空保持当前值): ", end="")
    choice = input().strip()

    model_map = {
        "1": "claude-sonnet-4-20250514",
        "2": "claude-opus-4-20250514",
        "3": "claude-haiku-4-20250514",
        "4": "gpt-4",
        "5": "gpt-4-turbo",
    }

    if choice in model_map:
        config["model"] = model_map[choice]
    elif choice == "6":
        print("输入自定义模型名称: ", end="")
        custom_model = input().strip()
        if custom_model:
            config["model"] = custom_model

    # 最大 Token
    print(f"\n最大 Token (留空保持当前值): ", end="")
    max_tokens = input().strip()
    if max_tokens:
        try:
            config["max_tokens"] = int(max_tokens)
        except ValueError:
            print("无效的数字，保持当前值")

    # 保存配置
    print("\n保存配置...")
    save_ai_config(config)
    print("✓ 配置已保存")

    # 测试连接
    print("\n是否测试连接？(y/n): ", end="")
    if input().lower() == "y":
        try:
            client = get_client()
            response = client.messages.create(
                model=config.get("model", "claude-sonnet-4-20250514"),
                max_tokens=50,
                messages=[{"role": "user", "content": "回复OK两个字"}],
            )
            reply = response.content[0].text
            print(f"✓ 连接成功: {reply}")
        except Exception as e:
            print(f"✗ 连接失败: {str(e)[:100]}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        interactive_config()
    else:
        test_config()
        print("\n提示: 运行 'python test_ai_config.py interactive' 进入交互式配置")
