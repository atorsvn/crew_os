from crew_os.enums import TaskState

class Task:
    _next_tid = 0

    def __init__(self, description: str, expected_output: str,
                 agent_id: int | None = None, # Can be assigned later by Scheduler/Crew Definition
                 dependencies: list[int] | None = None):
        self.tid = Task._next_tid
        Task._next_tid += 1
        self.description = description
        self.expected_output = expected_output # Helps guide agent simulation/LLM
        self.assigned_agent_id = agent_id # Who is *supposed* to do it (can be None initially)
        self.dependencies = dependencies if dependencies else [] # List of TIDs this task depends on
        self.state: TaskState = TaskState.PENDING # Start as pending
        self.context: str | None = None # Input gathered from dependencies' results
        self.result: str | None = None # Final output from this task

    def update_state(self, new_state: TaskState):
         # State changes logged by TaskManager/Scheduler
        self.state = new_state

    def add_context(self, context_data: str | None): # Allow setting context to None
        # Logged by TaskManager
        self.context = context_data

    def add_result(self, result_data: str):
        # Logged by TaskManager
        self.result = result_data

    def __str__(self):
        dep_str = f" Deps: {self.dependencies}" if self.dependencies else ""
        agent_str = f" Agent: {self.assigned_agent_id}" if self.assigned_agent_id is not None else " Agent: Unassigned"
        result_str = " Result: Yes" if self.result is not None else " Result: No"
        context_str = " Ctx: Yes" if self.context is not None else " Ctx: No"

        return (f"Task(TID: {self.tid}, State: {self.state.name},{agent_str},"
                f" Desc: '{self.description[:30]}...',{dep_str},{context_str},{result_str})")
