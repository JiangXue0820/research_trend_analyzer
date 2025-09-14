import requests
import json
from typing import List, Dict, Any, Union, Callable
from functools import partial
import logging
from google.genai.types import HttpOptions, Part
from google import genai
from configs.env_config import Config
from utils.helper_func import make_response


def mlops_inference(user_input, headers, model=None, temperature=None):
    messages = [{"role": "user", "content": '{}'.format(user_input)}]

    json_data = {
        "model": model,       # 模型名
        "stream": False,
        "messages": messages,
    }

    if temperature != None:
        json_data["temperature"] = temperature

    url = "http://mlops.huawei.com/mlops-service/api/v1/agentService/v1/chat/completions"
    response = requests.post(url, headers=headers, json=json_data, verify=False)
    result = json.loads(response.text)
    
    try:
        content = result["choices"][0]['message']['content']
        logging.info(f"[MLOPS] MLOps inference successful, model={model}, response (first 200): {content[:200]}")
        return make_response("success", "MLOps inference successful", content)
    
    except Exception as e:
        logging.exception(f"[MLOPS] MLOps inference failed, model={model}, error={e}")
        return make_response("error", f"MLOps inference failed: {e}", result)

def gemini_inference(user_input, api_key, model=None):

    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        logging.exception(f"[GEMINI] Failed to create Gemini client: {e}")
        return make_response("error", f"Failed to create Gemini client: {e}", None)
    
    try:
        response = client.models.generate_content(
            model=model,
            contents=user_input,
        )

    except Exception as e:
        logging.exception(f"[GEMINI] Gemini API call failed: {e}")
        return make_response("error", f"Gemini API call failed: {e}", None)
    
    try:
        content = response.text
        logging.info(f"[GEMINI] Gemini inference successful, model={model}.")
        return make_response("success", "Gemini inference successful", content)
    except Exception as e:
        logging.exception(f"[GEMINI] Failed to parse Gemini response: {e}")
        return make_response("error", f"Failed to parse Gemini response: {e}", None)
    

def get_llm(api: str, llm: str) -> Callable[[str], Any]:
    if api == "mlops":
        model = Config.ModelListMLOps.get(llm)
        if not model:
            raise ValueError(f"LLM '{llm}' not found in MLOps model list.")
        # 注意：partial 的第一个参数是函数对象，其后是要冻结的参数
        return partial(mlops_inference, headers=Config.MLOPS_HEADERS, model=model)

    elif api == "gemini":
        model = Config.ModelListGemini.get(llm)
        if not model:
            raise ValueError(f"LLM '{llm}' not found in Gemini model list.")
        return partial(gemini_inference, api_key=Config.GOOGLE_API_KEY, model=model)

    else:
        raise ValueError("api must be 'mlops' or 'gemini'")
