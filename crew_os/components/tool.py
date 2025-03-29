# crew_os/components/tool.py
from abc import ABC, abstractmethod
from crew_os.utils.logger import log
import math # For safer eval if needed, though direct functions better

class Tool(ABC):
    def __init__(self, name: str, description: str, cost: int = 1):
        self.name = name
        self.description = description # Crucial for LLM to understand the tool
        self.cost = cost # Simulated cost (e.g., tokens, API credits)

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """
        Executes the tool with arguments provided as keyword arguments.
        Should handle potential missing or incorrect arguments gracefully
        and return a string result or an informative error message.
        """
        pass

    def __str__(self):
        return f"Tool(name={self.name}, cost={self.cost})"

# --- Example Simulated Tools ---

class WebSearchTool(Tool):
    def __init__(self):
        super().__init__(
            name="web_search",
            description="Searches the web for a query. Requires string argument: 'query'.",
            cost=5
        )

    # Updated signature to accept keyword args and check specifically for 'query'
    def execute(self, **kwargs) -> str:
        query = kwargs.get("query")
        if not query or not isinstance(query, str):
             log(f"{self.name}", f"Error: Missing or invalid 'query' argument. Args received: {kwargs}")
             return "Error: Missing or invalid string argument 'query' for web_search tool."

        log(f"{self.name}", f"Simulating web search for: '{query}'")
        # Simulate finding relevant info based on the query
        result = f"Simulated search results for '{query}': Key AI trends for 2025 include Generative AI advancements in multimodal understanding, increased focus on AI ethics frameworks, and edge AI deployment in IoT devices."
        log(f"{self.name}", f"Finished search.")
        return result

class CalculatorTool(Tool):
    def __init__(self):
        super().__init__(
            name="calculator",
            description="Performs calculations on a mathematical expression. Requires string argument: 'expression'. Supports basic arithmetic (+, -, *, /).",
            cost=1
        )

    # Updated signature to accept keyword args and check for 'expression'
    def execute(self, **kwargs) -> str:
        expression = kwargs.get("expression")
        if not expression or not isinstance(expression, str):
             log(f"{self.name}", f"Error: Missing or invalid 'expression' argument. Args received: {kwargs}")
             return "Error: Missing or invalid string argument 'expression' for calculator tool."

        log(f"{self.name}", f"Simulating calculation for: '{expression}'")
        try:
            # Use a safer evaluation method if possible, or strictly parse known operations.
            # WARNING: eval is inherently risky. This is a slightly safer version for simulation.
            allowed_chars = "0123456789+-*/(). "
            if not all(c in allowed_chars for c in expression):
                raise ValueError("Expression contains invalid characters.")

            # Define a limited global scope for eval
            safe_globals = {"__builtins__": None}
            safe_locals = {} # Add math functions here if needed, e.g. {"sqrt": math.sqrt}

            result = str(eval(expression, safe_globals, safe_locals))
            log(f"{self.name}", f"Calculation result: {result}")
            return f"Result of '{expression}' is {result}"
        except Exception as e:
            log(f"{self.name}", f"Calculation failed for '{expression}': {e}")
            return f"Failed to calculate '{expression}': {e}"

# --- Tool Registry ---

class ToolRegistry:
    def __init__(self):
        self._tools = {} # name -> Tool instance

    def register_tool(self, tool: Tool):
        if tool.name in self._tools:
            log("ToolRegistry", f"Warning: Tool '{tool.name}' already registered. Overwriting.")
        self._tools[tool.name] = tool
        log("ToolRegistry", f"Registered tool: {tool.name}")

    def get_tool(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

    def get_tool_descriptions(self) -> str:
        """Returns a formatted string of tool names and descriptions for the LLM."""
        if not self._tools:
            return "No tools available."
        desc = "Available Tools:\n"
        for name, tool in self._tools.items():
            desc += f"- {name}: {tool.description} (Cost: {tool.cost})\n"
        return desc

# --- Default Registry Instance ---
# This instance is used by default in ToolDispatcher
default_tool_registry = ToolRegistry()
default_tool_registry.register_tool(WebSearchTool())
default_tool_registry.register_tool(CalculatorTool())
