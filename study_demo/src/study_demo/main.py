from study_demo.crew import StudyDemoCrew


def run():
    inputs = {
        "topic": "读取伊朗和美国的新闻并总结"
    }
    result = StudyDemoCrew().crew().kickoff(inputs=inputs)
    print("\n===== FINAL RESULT =====\n")
    print(result)


if __name__ == "__main__":
    run()