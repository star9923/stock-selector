# AI 配置自定义输入功能

## 功能说明

AI 分析配置现在支持自定义模型输入，不再局限于预设的模型列表。

## 使用方法

### 1. Web 界面配置

1. 打开系统设置页面
2. 找到"AI 分析配置"部分
3. 在"模型"输入框中：
   - **选择预设模型**：点击输入框，从下拉列表中选择常用模型
   - **自定义输入**：直接输入任意模型名称

#### 预设模型列表

- `claude-sonnet-4-20250514` - Claude Sonnet 4 (推荐)
- `claude-opus-4-20250514` - Claude Opus 4
- `claude-haiku-4-20250514` - Claude Haiku 4
- `claude-3-5-sonnet-20241022` - Claude 3.5 Sonnet
- `gpt-4` - GPT-4
- `gpt-4-turbo` - GPT-4 Turbo
- `gpt-3.5-turbo` - GPT-3.5 Turbo

#### 自定义模型示例

你可以输入任何兼容的模型名称，例如：
- `claude-opus-4-20250514`
- `gpt-4o`
- `deepseek-chat`
- `qwen-max`
- 其他第三方或自部署模型

### 2. 命令行配置

使用交互式配置工具：

```bash
python test_ai_config.py interactive
```

按照提示输入配置信息：
1. Base URL（API 端点）
2. API Key
3. 模型名称（可选择预设或自定义输入）
4. 最大 Token 数

### 3. 配置文件

配置保存在 `.cache/ai_config.json`：

```json
{
  "api_key": "your-api-key",
  "base_url": "https://api.anthropic.com",
  "model": "claude-sonnet-4-20250514",
  "max_tokens": 2000
}
```

你可以直接编辑此文件来修改配置。

## 配置项说明

### Base URL
- **默认值**: `https://api.anthropic.com`
- **说明**: API 端点地址
- **使用场景**:
  - 官方 API: `https://api.anthropic.com`
  - 第三方代理: 根据代理服务商提供的地址
  - 自部署服务: 你的服务器地址

### API Key
- **格式**: 通常以 `sk-` 或 `api-` 开头
- **安全**: 密钥加密存储在本地，不会上传
- **获取方式**:
  - Anthropic: https://console.anthropic.com/
  - OpenAI: https://platform.openai.com/api-keys
  - 其他服务商: 查看对应文档

### 模型名称
- **支持**: 任意字符串
- **建议**: 使用服务商提供的准确模型名称
- **验证**: 保存后使用"测试连接"功能验证

### 最大 Token
- **范围**: 500 - 8000
- **默认**: 2000
- **说明**: 单次分析的最大输出长度
- **建议**:
  - 简单分析: 1000-2000
  - 详细分析: 2000-4000
  - 深度分析: 4000-8000

## 兼容性

### Claude 系列
- ✅ Claude 4 系列（Opus, Sonnet, Haiku）
- ✅ Claude 3.5 系列
- ✅ Claude 3 系列

### OpenAI 系列
- ✅ GPT-4 系列
- ✅ GPT-3.5 系列
- ⚠️ 需要修改 Base URL 为 OpenAI 端点

### 其他模型
- ✅ 任何兼容 Anthropic Messages API 格式的模型
- ⚠️ 需要确保 API 格式兼容

## 测试连接

配置完成后，点击"测试连接"按钮验证：
- ✅ 连接成功: 显示 API 返回的测试消息
- ❌ 连接失败: 显示错误信息，检查配置是否正确

常见错误：
- `401 Unauthorized`: API Key 错误或无效
- `404 Not Found`: Base URL 或模型名称错误
- `Connection Error`: 网络问题或 Base URL 无法访问

## 使用场景

### 场景 1: 使用官方 Claude API
```
Base URL: https://api.anthropic.com
API Key: sk-ant-xxxxx
模型: claude-sonnet-4-20250514
```

### 场景 2: 使用第三方代理
```
Base URL: https://your-proxy.com/v1
API Key: your-proxy-key
模型: claude-sonnet-4-20250514
```

### 场景 3: 使用 OpenAI API
```
Base URL: https://api.openai.com/v1
API Key: sk-xxxxx
模型: gpt-4
```

### 场景 4: 使用自定义模型
```
Base URL: https://your-server.com/api
API Key: your-custom-key
模型: custom-model-v1
```

## 注意事项

1. **API Key 安全**
   - 不要在代码中硬编码 API Key
   - 不要将配置文件提交到版本控制
   - 定期更换 API Key

2. **模型兼容性**
   - 确保模型支持 Messages API 格式
   - 不同模型的 Token 限制可能不同
   - 某些模型可能不支持所有功能

3. **成本控制**
   - 不同模型的价格差异很大
   - 注意 Token 使用量
   - 建议先用较小的 max_tokens 测试

4. **性能考虑**
   - Opus 模型更强大但更慢更贵
   - Sonnet 模型平衡性能和成本
   - Haiku 模型快速但能力较弱

## 更新日志

- **2026-03-14**: 新增自定义模型输入功能
  - 模型选择从固定下拉框改为支持自定义输入
  - 添加常用模型快速选择列表
  - 支持任意模型名称输入
  - 新增交互式配置工具
