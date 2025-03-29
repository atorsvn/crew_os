from crew_os.utils.logger import log

class ResourceMonitor:
    def __init__(self):
        self.total_tokens_used = 0
        self.total_tool_calls = 0
        self.usage_log = [] # List of (type, agent_id, task_id, amount)

    def record_usage(self, usage_type: str, agent_id: int, task_id: int | None, amount: int):
        # Prevent recording zero usage
        if amount <= 0:
            return

        log("ResourceMonitor", f"Recording {amount} {usage_type} for Agent {agent_id} (Task {task_id})")
        if usage_type == "tokens":
            self.total_tokens_used += amount
        elif usage_type == "tool_calls":
            self.total_tool_calls += amount
        # Store detailed log if needed later
        self.usage_log.append((usage_type, agent_id, task_id, amount))
        # Add limit checks here if required

    def get_report(self) -> dict:
        return {
            "total_tokens": self.total_tokens_used,
            "total_tool_calls": self.total_tool_calls,
            # "detailed_log": self.usage_log # Uncomment if needed
        }
