from crew_os.enums import CrewProcess, AgentState, TaskState
from crew_os.components.agent import Agent
from crew_os.components.task import Task
from crew_os.core.task_manager import TaskManager
from crew_os.utils.logger import log
from collections import deque

class AgentScheduler:
    def __init__(self, agents: dict[int, Agent], task_manager: TaskManager, process: CrewProcess, task_order: list[int]):
        self.agents = agents # Agent pool managed by the scheduler
        self.task_manager = task_manager
        self.process = process
        # Used by sequential scheduler
        self.task_queue = deque(task_order) if process == CrewProcess.SEQUENTIAL else deque()
        # self.running_agent_task: dict[int, int] = {} # aid -> tid - Let Kernel manage this via states

    def get_available_agents(self) -> list[Agent]:
        return [a for a in self.agents.values() if a.state == AgentState.IDLE]

    def assign_task_to_agent(self, task: Task, agent: Agent):
        log("Scheduler", f"Assigning Task {task.tid} to Agent {agent.aid}")
        task.assigned_agent_id = agent.aid
        self.task_manager.update_task_state(task.tid, TaskState.ASSIGNED)
        agent.assign_task(task.tid) # Sets agent state to ASSIGNED
        # self.running_agent_task[agent.aid] = task.tid # Kernel will track based on state

    def release_agent(self, agent_id: int):
         agent = self.agents.get(agent_id)
         if agent:
             # Only release if it's not already idle (e.g. failed assignment)
             if agent.state != AgentState.IDLE:
                 log("Scheduler", f"Releasing Agent {agent_id} from state {agent.state.name} to IDLE.")
                 agent.update_state(AgentState.IDLE)
                 agent.current_task_id = None
             # if agent_id in self.running_agent_task:
             #     del self.running_agent_task[agent_id]


    def schedule_next(self):
        """
        Assigns READY tasks to IDLE agents based on the process.
        Also transitions ASSIGNED tasks to RUNNING if the agent is ready.
        Doesn't return pairs anymore, modifies states directly.
        """

        if self.process == CrewProcess.SEQUENTIAL:
            # 1. Check agents/tasks that are ASSIGNED and transition them to RUNNING
            assigned_tasks = [t for t in self.task_manager._tasks.values() if t.state == TaskState.ASSIGNED]
            made_running = 0
            for task in assigned_tasks:
                 agent = self.agents.get(task.assigned_agent_id)
                 # Check if agent is still assigned to this task and in ASSIGNED state
                 if agent and agent.current_task_id == task.tid and agent.state == AgentState.ASSIGNED:
                     log("Scheduler", f"Agent {agent.aid} starting Task {task.tid}.")
                     agent.update_state(AgentState.RUNNING_TASK)
                     self.task_manager.update_task_state(task.tid, TaskState.RUNNING)
                     # Build context *just before* running
                     self.task_manager.build_context(task)
                     made_running +=1
                     # In strict sequential, only allow one to start per tick?
                     # Or let kernel handle running one at a time if needed?
                     # Current logic allows multiple to be set RUNNING if assigned previously.
                     # Kernel._simulate_agent_work loop will process them.

            # If we started a task, maybe wait till next tick for new assignments?
            # Or allow assigning the next one immediately if an agent is free?
            # Let's allow assignment even if one just started running.

            # 2. If queue has items, check readiness and assign to idle agents
            if self.task_queue:
                next_tid_in_queue = self.task_queue[0] # Peek
                task = self.task_manager.get_task(next_tid_in_queue)

                # Ensure task dependencies are met *now* by checking/updating readiness
                self.task_manager.check_and_update_task_readiness()

                # Re-fetch task in case state changed
                task = self.task_manager.get_task(next_tid_in_queue)

                if task and task.state == TaskState.READY:
                    available_agents = self.get_available_agents()
                    if available_agents:
                        agent = available_agents[0] # Simple: take the first idle agent
                        log("Scheduler", f"Found READY Task {task.tid} in queue and IDLE Agent {agent.aid}.")
                        self.task_queue.popleft() # Dequeue *before* assigning
                        self.assign_task_to_agent(task, agent)
                        # Task is now ASSIGNED, agent is ASSIGNED.
                        # Will be set to RUNNING in the next tick's schedule_next() call (part 1).
                    else:
                        log("Scheduler", f"Task {next_tid_in_queue} is READY but no agents are IDLE.")
                elif task and task.state == TaskState.PENDING:
                     log("Scheduler", f"Next task {next_tid_in_queue} in queue is PENDING dependencies.")
                elif task and task.state in [TaskState.ASSIGNED, TaskState.RUNNING, TaskState.COMPLETED, TaskState.FAILED]:
                     log("Scheduler", f"Next task {next_tid_in_queue} in queue has unexpected state {task.state.name}. Removing.")
                     self.task_queue.popleft() # Remove already processed task
                elif not task:
                     log("Scheduler", f"Error: Task {next_tid_in_queue} from queue not found. Removing.")
                     self.task_queue.popleft() # Remove invalid task

        elif self.process == CrewProcess.HIERARCHICAL:
            log("Scheduler", "Hierarchical process not implemented yet.")
            pass

        # No return value needed, states are modified directly
