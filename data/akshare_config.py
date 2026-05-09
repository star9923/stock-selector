"""
akshare_config.py - AkShare 统一配置
在所有使用 akshare 的模块之前导入此模块
"""
import os
import socket
import warnings

# 必须在导入 requests/akshare 之前设置
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'

# 清除所有代理设置
for key in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY',
            'all_proxy', 'ALL_PROXY', 'ftp_proxy', 'FTP_PROXY',
            'socks_proxy', 'SOCKS_PROXY']:
    os.environ.pop(key, None)

# 全局 socket 超时（秒）：防止 AkShare 底层 requests 未显式设超时而无限挂起
socket.setdefaulttimeout(15)

# 忽略 SSL 警告
warnings.filterwarnings('ignore', category=Warning)

# 配置 urllib3
import urllib3
urllib3.disable_warnings()

print("   ℹ️  已禁用代理，直连 API (socket timeout=15s)")
