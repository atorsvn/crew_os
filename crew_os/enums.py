from enum import Enum, auto

class AgentState(Enum):
    IDLE = auto()
    ASSIGNED = auto() # Task assigned, not yet running
    RUNNING_TASK = auto()
    USING_TOOL = auto() # Waiting for a sync tool call simulation / execution
    WAITING_DELEGATION = auto() # For hierarchical process
    TERMINATED = auto() # Not used yet, but good for future

class TaskState(Enum):
    PENDING = auto() # Waiting for dependencies or scheduling
    READY = auto() # Dependencies met, ready to be scheduled
    ASSIGNED = auto() # Assigned to an agent
    RUNNING = auto() # Actively being worked on
    WAITING_CONTEXT = auto() # Should not happen if deps handled correctly
    COMPLETED = auto()
    FAILED = auto()

class CrewProcess(Enum):
    SEQUENTIAL = auto()
    HIERARCHICAL = auto() # Not implemented in this version
    # PARALLEL = auto() # Could be another future process
