from pathlib import Path
import os
import sys

from dotenv import load_dotenv

# 为了支持直接运行 main.py，这里把 src 目录加入模块搜索路径。
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 从项目根目录加载 .env 环境变量。
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from study_demo.crew import StudyDemoCrew


def analyze_topic(topic: str) -> str:
    topic = topic.strip()
    if not topic:
        raise ValueError("主题不能为空")

    inputs = {"topic": topic}
    result = StudyDemoCrew().crew().kickoff(inputs=inputs)
    return str(result)


def run():
    topic = input("请输入你想分析的主题：").strip()

    if not topic:
        print("主题不能为空")
        return

    result = analyze_topic(topic)

    print("\n===== FINAL RESULT =====\n")
    print(result)


if __name__ == "__main__":
    run()
