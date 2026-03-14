import os
from dotenv import load_dotenv


env_path = '.env.llm'
load_dotenv(env_path)


def require_env(name:str)->str:
    value = os.getenv(name)

    if not value:
        raise ValueError(f"Missing {name} variable env")
    
    return value


BIELIK_API_KEY= require_env("BIELIK_API_KEY")
BIELIK_BASE_URL= require_env("BIELIK_BASE_URL")
BIELIK_MODEL= require_env("BIELIK_MODEL")

AI_DEVS_API=require_env("AI_DEVS_API")
AI_DEVS_BASE_URL=require_env("AI_DEVS_BASE_URL")