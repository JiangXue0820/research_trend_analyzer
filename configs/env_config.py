import os
from dotenv import load_dotenv

class Config:
    load_dotenv()

    # MLOps API 密钥
    MLOPS_API_KEY = os.getenv('MLOPS_API_KEY', '')
    MLOPS_HEADERS = {
        'Authorization': f"Bearer {MLOPS_API_KEY}",
    }

    # Google API 密钥
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')

    # 代理配置
    PROXY_ID = os.getenv('PROXY_ID', '')
    PROXY_PW = os.getenv('PROXY_PW', '')

    if PROXY_ID and PROXY_PW:
        PROXY = {
            "http": f"http://{PROXY_ID}:{PROXY_PW}@proxyhk.huawei.com:8080",
            "https": f"http://{PROXY_ID}:{PROXY_PW}@proxyhk.huawei.com:8080"
        }
    else:
        PROXY = None
    
    ModelListMLOps = {
        "llama3.3-70b": "Meta-Llama-3.3-70B-Instruct-MLOPS",
        "qwen2.5-72b": "Qwen2.5-72B",
        "qwen2.5-7b": "qwen2.5-7b-instruct",
        "qwen3-32b": "qwen3-32b",
      }
    
    ModelListGemini = {
        "gemini-1.5-pro": "gemini-1.5-pro",
        "gemini-2.5-flash": "gemini-2.5-flash",
    }
