from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task


@CrewBase
class StudyDemoCrew:
    """StudyDemo pipeline."""

    @agent
    def planner(self) -> Agent:
        return Agent(
            config=self.agents_config["planner"],
            verbose=True,
        )

    @agent
    def researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["researcher"],
            verbose=True,
        )

    @agent
    def reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["reviewer"],
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
            agents=[self.planner(), self.researcher(), self.reviewer()],
            tasks=[self.plan_task(), self.research_task(), self.review_task()],
            process=Process.sequential,
            verbose=True,
        )
