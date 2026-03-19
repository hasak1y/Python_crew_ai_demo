from pathlib import Path
import os

from crewai import Agent, Crew, LLM, Process, Task
from crewai.project import CrewBase, agent, crew, task
from dotenv import load_dotenv

# 在导入阶段先加载 .env，确保显式绑定模型时能读到配置。
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# 显式创建一个共享的模型实例，供三个 agent 复用。
deepseek_llm = LLM(
    model=os.getenv("OPENAI_MODEL_NAME", "deepseek-chat"),
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_API_BASE", "https://api.deepseek.com/v1"),
)


@CrewBase
class StudyDemoCrew:
    """3-agent study demo crew"""

    @agent
    def planner(self) -> Agent:
        return Agent(
            config=self.agents_config["planner"],
            llm=deepseek_llm,
            verbose=True,
        )

    @agent
    def researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["researcher"],
            llm=deepseek_llm,
            verbose=True,
        )

    @agent
    def reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["reviewer"],
            llm=deepseek_llm,
            verbose=True,
        )

    @task
    def plan_task(self) -> Task:
        return Task(
            config=self.tasks_config["plan_task"],
        )

    @task
    def research_task(self) -> Task:
        return Task(
            config=self.tasks_config["research_task"],
        )

    @task
    def review_task(self) -> Task:
        return Task(
            config=self.tasks_config["review_task"],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[
                self.planner(),
                self.researcher(),
                self.reviewer(),
            ],
            tasks=[
                self.plan_task(),
                self.research_task(),
                self.review_task(),
            ],
            process=Process.sequential,
            verbose=True,
        )
