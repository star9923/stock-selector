"""
network_helper.py - 网络请求重试工具
解决 ConnectionResetError(10054) 等网络错误
"""
import time
import socket
from functools import wraps


def retry_on_connection_error(max_retries=3, delay=2, timeout=30):
    """
    网络请求重试装饰器
    :param max_retries: 最大重试次数
    :param delay: 重试间隔（秒）
    :param timeout: socket 超时时间（秒）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            original_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(timeout)

            for attempt in range(max_retries):
                try:
                    result = func(*args, **kwargs)
                    socket.setdefaulttimeout(original_timeout)
                    return result
                except (ConnectionResetError, ConnectionAbortedError,
                        socket.timeout, OSError) as e:
                    if attempt < max_retries - 1:
                        print(f"   ⚠️  连接错误，{delay}秒后重试 ({attempt + 1}/{max_retries})")
                        time.sleep(delay)
                    else:
                        print(f"   ❌ 连接失败: {str(e)[:80]}")
                        socket.setdefaulttimeout(original_timeout)
                        raise
                except Exception as e:
                    socket.setdefaulttimeout(original_timeout)
                    raise

            socket.setdefaulttimeout(original_timeout)
            return None
        return wrapper
    return decorator
