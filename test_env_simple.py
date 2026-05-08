import os

try:
    from dotenv import load_dotenv
    load_dotenv()
    print("load_dotenv called successfully")
except ImportError:
    print("python-dotenv not installed")

print("=== Environment Variables ===")
print("SERPER_API_KEY:", os.getenv('SERPER_API_KEY', 'NOT FOUND')[:20] + '...' if os.getenv('SERPER_API_KEY') else 'NOT FOUND')
print("DASHSCOPE_API_KEY:", os.getenv('DASHSCOPE_API_KEY', 'NOT FOUND')[:20] + '...' if os.getenv('DASHSCOPE_API_KEY') else 'NOT FOUND')
print("LLM_MODEL:", os.getenv('LLM_MODEL', 'NOT FOUND'))
print("LLM_BASE_URL:", os.getenv('LLM_BASE_URL', 'NOT FOUND'))
print("MAX_TOTAL_SEARCHES:", os.getenv('MAX_TOTAL_SEARCHES', 'NOT FOUND'))
print("SERPER_TIMEOUT_SECONDS:", os.getenv('SERPER_TIMEOUT_SECONDS', 'NOT FOUND'))
print("LLM_TIMEOUT_SECONDS:", os.getenv('LLM_TIMEOUT_SECONDS', 'NOT FOUND'))
print("SERVER_PORT:", os.getenv('SERVER_PORT', 'NOT FOUND'))

print("\n=== Checking if env file values match ===")
print("SERPER_API_KEY matches .env:", os.getenv('SERPER_API_KEY') == '52ff43c1b1c84ad2a3307929704e2cae80be2eef')
print("DASHSCOPE_API_KEY matches .env:", os.getenv('DASHSCOPE_API_KEY') == 'sk-b4a5eb3d904c4e31876054ff8465102a')
print("LLM_MODEL matches .env:", os.getenv('LLM_MODEL') == 'qwen3.5-flash')
