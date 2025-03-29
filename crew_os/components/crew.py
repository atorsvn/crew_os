from crew_os.enums import CrewProcess, TaskState, AgentState # Import states
from crew_os.components.agent import Agent
from crew_os.components.task import Task

class Crew:
    def __init__(self, agents: list[Agent], tasks: list[Task], process: CrewProcess):
        self.agents: dict[int, Agent] = {agent.aid: agent for agent in agents}
        self.tasks: dict[int, Task] = {task.tid: task for task in tasks}
        self.process: CrewProcess = process
        # For sequential process, maintain the original order of TIDs
        self.task_order: list[int] = [task.tid for task in tasks]
        # Could add crew-level resource limits or shared context here

    def get_agent(self, aid: int) -> Agent | None:
        return self.agents.get(aid)

    def get_task(self, tid: int) -> Task | None:
        return self.tasks.get(tid)

    def get_tasks_by_state(self, state: TaskState) -> list[Task]:
        return [t for t in self.tasks.values() if t.state == state]

    def get_agents_by_state(self, state: AgentState) -> list[Agent]:
        return [a for a in self.agents.values() if a.state == state]

    def all_tasks_done(self) -> bool:
        """Checks if all tasks are in a terminal state (COMPLETED or FAILED)."""
        return all(t.state in [TaskState.COMPLETED, TaskState.FAILED] for t in self.tasks.values())

    def reset_states(self):
        """Resets agents and tasks to initial states for a re-run."""
        Agent._next_aid = 0 # Reset AID counter if needed for predictable IDs in demos
        Task._next_tid = 0 # Reset TID counter
        for agent in self.agents.values():
            agent.state = AgentState.IDLE
            agent.current_task_id = None
            agent.resource_usage = {"tokens": 0, "tool_calls": 0}
        for task in self.tasks.values():
            task.state = TaskState.PENDING # Reset to PENDING
            task.context = None
            task.result = None
            # Re-check dependencies after reset? Should be fine if structure doesn't change.
