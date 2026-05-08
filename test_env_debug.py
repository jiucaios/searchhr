"""测试环境变量读取调试"""
import os

# 尝试加载.env文件
try:
    from dotenv import load_dotenv
    print("✓ 成功导入python-dotenv")
    load_dotenv()
    print("✓ 成功加载.env文件")
except ImportError as e:
    print(f"✗ 导入失败: {e}")

print("\n=== 环境变量读取结果 ===")
print(f"环境变量 SERPER_API_KEY: {os.getenv('SERPER_API_KEY', '未找到')}")
print(f"代码中的 DEMO_SERPER_API_KEY 默认值: 52ff43c1b1c84ad2a3307929704e2cae80be2eef")
print(f"\n两个值是否相同: {os.getenv('SERPER_API_KEY') == '52ff43c1b1c84ad2a3307929704e2cae80be2eef'}")
