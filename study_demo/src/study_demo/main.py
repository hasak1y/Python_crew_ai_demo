from pathlib import Path

from dotenv import load_dotenv

from study_demo.crew import StudyDemoCrew


load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def run():
    topic = input("请输入你想分析的主题：").strip()
    if not topic:
        print("主题不能为空。")
        return

    inputs = {"topic": topic}
    result = StudyDemoCrew().crew().kickoff(inputs=inputs)
    print("\n===== FINAL RESULT =====\n")
    print(result)


if __name__ == "__main__":
    run()
