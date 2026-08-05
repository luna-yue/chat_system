"""Agent 服务配置 — 优先环境变量, 其次 .env 文件, 不硬编码"""

import os
from pathlib import Path

# 加载 .env (若存在, 且未通过环境变量注入)
_env_path = Path(__file__).parent / ".env"
if _env_path.exists() and not os.getenv("DEEPSEEK_API_KEY"):
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

# LLM API 配置
LLM_API_KEY = os.getenv("DEEPSEEK_API_KEY", "your-api-key-here")
LLM_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
LLM_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# LLM 参数
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1024"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))  # 秒

# 服务配置
SERVICE_HOST = os.getenv("SERVICE_HOST", "0.0.0.0")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8080"))
