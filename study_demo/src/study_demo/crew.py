from pathlib import Path
import os
import sys

from crewai import Agent, Crew, LLM, Process, Task
from crewai.project import CrewBase, agent, crew, task
from dotenv import load_dotenv

from study_demo.tools.project_tools import list_project_files, read_local_file

# 在 Windows 终端中统一切换为 UTF-8 输出，避免 CrewAI 日志里的 emoji 触发 gbk 编码错误。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="ignore")

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
    """Hybrid research demo crew."""

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
            tools=[list_project_files, read_local_file],
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
        # 当前启用混合模式：保留 planner、researcher、reviewer，
        # 但只有在题目和本地资料相关时，researcher 才需要使用 knowledge 工具。
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
