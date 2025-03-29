# crew_os/core/tool_dispatcher.py
from crew_os.components.tool import ToolRegistry, default_tool_registry, Tool
from crew_os.components.agent import Agent
from crew_os.components.crew import Crew # <-- Import Crew
from crew_os.core.resource_monitor import ResourceMonitor
from crew_os.utils.logger import log

class ToolDispatcher:
    # Accept crew reference to access agent's allowed tools
    def __init__(self, resource_monitor: ResourceMonitor, tool_registry: ToolRegistry = default_tool_registry, crew: Crew | None = None):
        self.tool_registry = tool_registry
        self.resource_monitor = resource_monitor
        self.crew = crew # Store crew reference
        if not crew:
             log("ToolDispatcher", "Warning: Crew reference not provided to ToolDispatcher. Agent tool authorization cannot be checked.")

    # Modify execute_tool to accept **kwargs for flexibility with LLM arguments
    def execute_tool(self, agent: Agent, task_id: int | None, tool_name: str, **kwargs) -> str:
        """
        Executes a tool requested by an agent.

        Args:
            agent (Agent): The agent requesting the tool.
            task_id (int | None): The ID of the task the agent is working on.
            tool_name (str): The name of the tool to execute.
            **kwargs: Arguments for the tool provided by the LLM.

        Returns:
            str: The result of the tool execution or an error message.
        """
        log("ToolDispatcher", f"Agent {agent.aid} requests tool '{tool_name}' with args {kwargs} for Task {task_id}")

        # --- Authorization Check ---
        agent_obj = self.crew.get_agent(agent.aid) if self.crew else None # Get full Agent object
        if not agent_obj:
             msg = f"Agent {agent.aid} not found in crew. Cannot authorize tool '{tool_name}'."
             log("ToolDispatcher", f"Error: {msg}")
             return f"Error: Agent {agent.aid} not found." # Return error to LLM

        if tool_name not in agent_obj.tools:
             msg = f"Agent {agent.aid} (Role: {agent_obj.role}) is not authorized to use tool '{tool_name}'. Allowed tools: {agent_obj.tools}"
             log("ToolDispatcher", f"Error: {msg}")
             return f"Error: You are not authorized to use the tool '{tool_name}'. Available tools: {agent_obj.tools}" # Return specific error to LLM

        # --- Tool Finding ---
        tool: Tool | None = self.tool_registry.get_tool(tool_name)
        if not tool:
            msg = f"Tool '{tool_name}' not found in registry."
            log("ToolDispatcher", f"Error: {msg}")
            return f"Error: Tool '{tool_name}' not found in the system." # Return error to LLM

        # --- Resource Recording ---
        log("ToolDispatcher", f"Recording usage for tool '{tool_name}' (Cost: {tool.cost})")
        self.resource_monitor.record_usage("tool_calls", agent.aid, task_id, 1)
        # Use tool cost as token estimate for resource monitor
        self.resource_monitor.record_usage("tokens", agent.aid, task_id, tool.cost)
        # Agent resource tracking
        agent.record_usage("tool_calls", 1)
        agent.record_usage("tokens", tool.cost)

        # --- Execution ---
        try:
            # Execute tool using keyword arguments provided by the LLM
            log("ToolDispatcher", f"Executing tool '{tool_name}' with arguments: {kwargs}")
            result = tool.execute(**kwargs) # Use **kwargs
            log("ToolDispatcher", f"Tool '{tool_name}' executed successfully by Agent {agent.aid}.")
            # Return the actual result string - ensure it's not excessively long?
            return str(result) # Ensure result is string
        except TypeError as e:
             # Handle cases where LLM provided wrong/unexpected arguments for the tool's execute method
             log("ToolDispatcher", f"Error executing tool '{tool_name}' due to argument mismatch: {e}")
             import inspect
             expected_args = inspect.signature(tool.execute)
             # Provide helpful error back to LLM
             return f"Error: Tool '{tool_name}' failed. Incorrect arguments provided. Expected arguments: {expected_args}. Error: {e}"
        except Exception as e:
            log("ToolDispatcher", f"Error executing tool '{tool_name}' for Agent {agent.aid}: {type(e).__name__} - {e}")
            # Return an error message that the LLM might understand
            return f"Error executing tool '{tool_name}': {type(e).__name__} - {e}"
