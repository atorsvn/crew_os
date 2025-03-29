from crew_os.enums import AgentState
# Remove direct tool import if only names used, keep for type hinting if Tool objects passed
# from crew_os.components.tool import Tool

class Agent:
    _next_aid = 0

    def __init__(self, role: str, goal: str, backstory: str, tools: list[str] | None = None):
        self.aid = Agent._next_aid
        Agent._next_aid += 1
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.tools = tools if tools else [] # List of tool *names* agent can use
        self.state: AgentState = AgentState.IDLE
        self.current_task_id: int | None = None
        self.resource_usage = {"tokens": 0, "tool_calls": 0} # Simple tracking

    def update_state(self, new_state: AgentState):
        # Avoid redundant logging if state doesn't change
        # if self.state != new_state:
            # log inside scheduler/kernel where state change originates
        self.state = new_state

    def assign_task(self, task_id: int):
        self.current_task_id = task_id
        self.update_state(AgentState.ASSIGNED)

    def record_usage(self, usage_type: str, amount: int):
        if amount <= 0: return # Don't record zero usage
        if usage_type in self.resource_usage:
            self.resource_usage[usage_type] += amount
        else:
            # Silently ignore unknown resource types for now
            pass

    def __str__(self):
        usage_str = f"Usage(T:{self.resource_usage['tokens']}, C:{self.resource_usage['tool_calls']})"
        return (f"Agent(AID: {self.aid}, Role: {self.role}, State: {self.state.name}, "
                f"Task: {self.current_task_id}, Tools: {self.tools}, {usage_str})")
