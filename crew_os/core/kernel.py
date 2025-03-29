# crew_os/core/kernel.py
import ollama # <-- Import the library
import json   # <-- To parse LLM response
import random # Keep for now if needed elsewhere, but not for core logic
import time
from crew_os.enums import CrewProcess, AgentState, TaskState
from crew_os.components.agent import Agent # <-- Import Agent for type hint
from crew_os.components.task import Task   # <-- Import Task for type hint
from crew_os.components.crew import Crew
from crew_os.core.scheduler import AgentScheduler
from crew_os.core.task_manager import TaskManager
from crew_os.core.tool_dispatcher import ToolDispatcher
from crew_os.core.resource_monitor import ResourceMonitor
from crew_os.utils.logger import log

class Kernel:
    # Add ollama_model parameter
    def __init__(self, ollama_model: str = "llama3"): # Default model
        self.crew: Crew | None = None
        self.task_manager: TaskManager | None = None
        self.scheduler: AgentScheduler | None = None
        self.tool_dispatcher: ToolDispatcher | None = None
        self.resource_monitor: ResourceMonitor | None = None
        self.tick_count = 0
        self.running = False
        self.ollama_model = ollama_model # Store the model name
        log("Kernel", f"Initialized with Ollama model: {self.ollama_model}")
        # Ensure Ollama is reachable (optional basic check)
        try:
             log("Kernel", f"Attempting to connect to Ollama...")
             available_models = ollama.list().get('models', [])
             log("Kernel", f"Available Ollama models: {[m['name'] for m in available_models]}")
             # Check if desired model is available
             model_found = any(m['name'].startswith(self.ollama_model) for m in available_models)
             if not model_found:
                  log("Kernel", f"Warning: Model '{self.ollama_model}' not found in Ollama. Please ensure it is pulled.")
             else:
                 log("Kernel", f"Model '{self.ollama_model}' appears available.")
        except Exception as e:
             log("Kernel", f"Warning: Could not connect to Ollama or list models: {e}")
             log("Kernel", "Ensure Ollama is running (e.g., `ollama serve` or desktop app) and the model '{self.ollama_model}' is pulled (`ollama pull {self.ollama_model}`).")


    def load_crew(self, crew: Crew):
        log("Kernel", f"Loading Crew with Process: {crew.process.name}")
        self.crew = crew
        # Initialize core components with crew data
        self.resource_monitor = ResourceMonitor()
        # Pass resource monitor and crew to dispatcher
        self.tool_dispatcher = ToolDispatcher(self.resource_monitor, crew=self.crew)
        self.task_manager = TaskManager(self.crew.tasks)
        self.scheduler = AgentScheduler(
            self.crew.agents,
            self.task_manager,
            self.crew.process,
            self.crew.task_order # Pass original task order for sequential
        )
        self.tick_count = 0
        self.running = False
        log("Kernel", "Crew loaded successfully.")

    def _build_llm_prompt(self, agent: Agent, task: Task, tool_results: dict | None = None) -> list[dict]:
        """Builds the messages list for the Ollama chat API."""

        # --- System Prompt ---
        system_prompt = f"""You are an AI agent simulating the role of '{agent.role}'.
Your overall goal is: {agent.goal}.
Your background: {agent.backstory}.

You are currently working on the following task:
Task Description: {task.description}
Expected Output: {task.expected_output}
"""
        if task.context:
            system_prompt += f"""\nYou have the following context from previous tasks:\n---CONTEXT START---\n{task.context}\n---CONTEXT END---\n"""

        # --- Tool Information ---
        available_tools_details = []
        if agent.tools and self.tool_dispatcher:
            system_prompt += "\nYou have access to the following tools:\n"
            for tool_name in agent.tools:
                tool = self.tool_dispatcher.tool_registry.get_tool(tool_name)
                if tool:
                    available_tools_details.append({"name": tool.name, "description": tool.description})
                    system_prompt += f"- {tool.name}: {tool.description}\n"
        else:
             system_prompt += "\nYou have no tools available.\n"

        # --- Response Format Instruction ---
        system_prompt += """
Based on the task, context, and available tools, decide your next action.
Respond ONLY with a JSON object containing ONE of the following structures:

1.  To use a tool:
    {
      "action": "use_tool",
      "tool_name": "<name_of_tool_to_use>",
      "arguments": { "<argument_name>": "<argument_value>", ... }
    }
    (Make sure 'arguments' is a JSON object, containing only the required arguments for the chosen tool. If a tool takes no arguments, use {}).

2.  To provide the final answer for the current task:
    {
      "action": "final_answer",
      "content": "<your_complete_final_answer_for_the_task>"
    }

Choose the action that best progresses the task towards the expected output.
If you use a tool, I will provide the result, and you will decide the next step.
Be precise and stick strictly to the JSON format. Do not add any explanations or text outside the JSON structure. Just the JSON object.
"""
        messages = [{"role": "system", "content": system_prompt}]

        # --- Include Tool Results if any ---
        if tool_results:
             user_prompt = "You previously used tools. Here are the results:\n"
             for tool_name, result in tool_results.items():
                 user_prompt += f"--- Result from {tool_name} ---\n{result}\n--- End {tool_name} ---\n\n"
             user_prompt += "Now, decide your next action based on these results and the original task. Respond ONLY with the JSON structure."
             messages.append({"role": "user", "content": user_prompt})
        else:
            # Initial prompt for the task
             messages.append({"role": "user", "content": "What is your first action to accomplish the task? Respond ONLY with the JSON structure."})


        return messages


    def _call_ollama(self, agent: Agent, task: Task, messages: list[dict]) -> dict | None:
        """Calls the Ollama API and parses the JSON response."""
        log("Kernel", f"Agent {agent.aid} calling Ollama model {self.ollama_model} for Task {task.tid}")
        # Simulate token cost for the call itself (can be refined)
        # Actual token counts might be available in response, depending on library/model
        call_cost = 100 # Base cost estimate per LLM interaction (prompt+response)
        self.resource_monitor.record_usage("tokens", agent.aid, task.tid, call_cost)
        agent.record_usage("tokens", call_cost)

        raw_content = "Error: No response received" # Default error message
        try:
            response = ollama.chat(
                model=self.ollama_model,
                messages=messages,
                format='json', # Request JSON output format
                options={ # Optional: Adjust parameters as needed
                     "temperature": 0.5, # Lower temperature for more deterministic JSON output
                     "num_predict": 512, # Limit response length
                 }
            )

            # Log raw response content for debugging
            raw_content = response.get('message', {}).get('content', 'Error: No content in message')
            log("Kernel", f"Ollama raw response for Agent {agent.aid}: {raw_content}")

            # Attempt to strip potential markdown ```json ... ``` wrappers if present
            if raw_content.strip().startswith("```json"):
                 log("Kernel", "Detected JSON markdown wrapper, attempting to strip.")
                 raw_content = raw_content.strip()[7:-3].strip() # Remove ```json and ```

            # Parse the JSON content
            parsed_response = json.loads(raw_content)
            log("Kernel", f"Ollama parsed response for Agent {agent.aid}: {parsed_response}")

            # Optional: Record actual output tokens if needed/possible
            # try:
            #     prompt_tokens = response.get('prompt_eval_count', 0)
            #     response_tokens = response.get('eval_count', 0)
            #     # Adjust resource monitor based on actuals (might need to adjust base cost logic)
            # except Exception: pass # Ignore if token counts aren't available

            return parsed_response

        except ollama.ResponseError as e:
            log("Kernel", f"Error: Ollama API error for Agent {agent.aid}, Task {task.tid}: {e.error}")
            # hasattr check removed as per ollama library examples
            log("Kernel", f"Ollama status code: {e.status_code}")
        except json.JSONDecodeError as e:
            log("Kernel", f"Error: Could not parse JSON response from Ollama for Agent {agent.aid}, Task {task.tid}: {e}")
            log("Kernel", f"Raw non-JSON response was: {raw_content}") # Log the invalid response
        except Exception as e:
            log("Kernel", f"Error: Unexpected error during Ollama call for Agent {agent.aid}, Task {task.tid}: {type(e).__name__} - {e}")

        return None # Indicate failure


    # *** Replace the simulation logic with LLM calls ***
    def _simulate_agent_work(self, agent: Agent, task: Task) -> bool:
        """Performs one step of agent work using Ollama."""
        log("Kernel", f"Agent {agent.aid} starting work cycle for Task {task.tid}")

        # --- Initial Call ---
        current_tool_results = {} # Store results if a tool is used in this cycle

        # Build the initial prompt
        messages = self._build_llm_prompt(agent, task)

        # Make the first call to Ollama
        llm_response = self._call_ollama(agent, task, messages)

        # Check for basic validity
        if not isinstance(llm_response, dict) or "action" not in llm_response:
            log("Kernel", f"Agent {agent.aid} failed to get valid action JSON from LLM. Task {task.tid} might fail. Check Ollama logs.")
            # Task doesn't complete, agent remains RUNNING_TASK, will retry next tick
            return False

        action = llm_response.get("action")

        # --- Handle Tool Use Action ---
        if action == "use_tool":
            tool_name = llm_response.get("tool_name")
            tool_args_dict = llm_response.get("arguments", {}) # Ensure args is a dict

            if not isinstance(tool_args_dict, dict):
                log("Kernel", f"Error: LLM provided invalid 'arguments' format for tool '{tool_name}'. Expected a dict, got {type(tool_args_dict)}. Agent {agent.aid}, Task {task.tid}")
                return False # Cannot proceed this tick

            if not tool_name:
                 log("Kernel", f"Error: LLM action 'use_tool' missing 'tool_name'. Agent {agent.aid}, Task {task.tid}")
                 return False # Cannot proceed this tick

            log("Kernel", f"Agent {agent.aid} decided to use tool '{tool_name}' with args: {tool_args_dict}")
            agent.update_state(AgentState.USING_TOOL) # Mark state

            # Execute the tool *synchronously*
            tool_result = self.tool_dispatcher.execute_tool(agent, task.tid, tool_name, **tool_args_dict) # Use ** to unpack dict as kwargs

            log("Kernel", f"Agent {agent.aid} received tool result for '{tool_name}': '{str(tool_result)[:150]}...'")
            current_tool_results[tool_name] = str(tool_result) # Store result as string

            # --- Second Call (After Tool Use) ---
            # Now, build a new prompt including the tool result and ask for the next action
            log("Kernel", f"Agent {agent.aid} making second LLM call after using tool '{tool_name}'.")
            messages = self._build_llm_prompt(agent, task, tool_results=current_tool_results)

            # Make the second call to Ollama
            llm_response = self._call_ollama(agent, task, messages)

            if not isinstance(llm_response, dict) or "action" not in llm_response:
                 log("Kernel", f"Agent {agent.aid} failed to get valid action JSON from LLM after using tool. Task {task.tid} might fail.")
                 agent.update_state(AgentState.RUNNING_TASK) # Back to running, but maybe stuck
                 return False # Task not completed

            action = llm_response.get("action")

            # Agent should ideally provide final answer now, but could theoretically chain tools (add loop here if needed)
            if action == "use_tool":
                log("Kernel", f"Warning: Agent {agent.aid} wants to use another tool immediately after the first. Simple model: Will proceed only if next action is final_answer. Task {task.tid}")
                # This simple model doesn't support chaining tools within one work cycle.
                # We will fall through and check if the action *now* is final_answer.


        # --- Handle Final Answer Action ---
        # This check happens either on the first call (if no tool needed) or second call (after tool use)
        if action == "final_answer":
            final_content = llm_response.get("content")
            if final_content is None:
                 log("Kernel", f"Error: LLM action 'final_answer' missing 'content'. Agent {agent.aid}, Task {task.tid}")
                 agent.update_state(AgentState.RUNNING_TASK) # Stuck
                 return False # Task not completed

            log("Kernel", f"Agent {agent.aid} provided final answer for Task {task.tid}.")
            self.task_manager.add_result(task.tid, str(final_content)) # Ensure result is string
            self.task_manager.update_task_state(task.tid, TaskState.COMPLETED)
            self.scheduler.release_agent(agent.aid)
            # Check if newly completed task makes others ready
            self.task_manager.check_and_update_task_readiness()
            # Agent state is set to IDLE by release_agent
            return True # Task completed

        # --- Handle Other/Failed Cases ---
        else:
            log("Kernel", f"Agent {agent.aid} returned unknown or unhandled action '{action}' or failed to decide after tool use. Task {task.tid}")
            agent.update_state(AgentState.RUNNING_TASK) # Still running, but potentially stuck
            return False # Task not completed


    # ... (tick, run methods updated slightly below) ...

    def tick(self) -> bool:
        """Runs one simulation step (tick). Returns True if simulation should continue."""
        if not self.crew or not self.scheduler or not self.task_manager or not self.tool_dispatcher:
             log("Kernel", "Error: Crew or core components not loaded.")
             return False

        if not self.running:
            # Don't log this every time if just stepping with 'tick' command
            # log("Kernel", "Simulation not started.")
            return False

        self.tick_count += 1
        log("Kernel", f"--- Tick {self.tick_count} Start ---")

        # 1. Schedule next tasks/agents
        # Assigns ready tasks to idle agents (-> ASSIGNED state)
        # Sets ASSIGNED tasks with available agents to RUNNING state for this tick
        self.scheduler.schedule_next() # Modifies states directly

        # 2. Simulate work for agents whose tasks are in the RUNNING state
        running_tasks = self.crew.get_tasks_by_state(TaskState.RUNNING)

        if not running_tasks:
            log("Kernel", "No tasks currently in RUNNING state.")


        for task in running_tasks:
             # Check task state again, as it might have changed if multiple agents run sequentially
             if task.state != TaskState.RUNNING:
                 continue

             agent = self.crew.get_agent(task.assigned_agent_id)

             if agent and agent.state == AgentState.RUNNING_TASK:
                 # Call the LLM-based work simulation
                 task_completed = self._simulate_agent_work(agent, task)
                 if task_completed:
                     log("Kernel", f"Task {task.tid} processing completed during tick {self.tick_count}.")
                     # State changes (task COMPLETED, agent IDLE) are handled within _simulate_agent_work
                 else:
                     # Task not completed, agent remains RUNNING_TASK
                     log("Kernel", f"Task {task.tid} not completed this tick.")

             elif agent:
                 log("Kernel", f"Warning: Task {task.tid} is RUNNING but assigned Agent {agent.aid} state is {agent.state.name}. Skipping work simulation this tick.")
             else:
                 log("Kernel", f"Error: Task {task.tid} is RUNNING but assigned Agent {task.assigned_agent_id} not found.")


        log("Kernel", f"--- Tick {self.tick_count} End ---")

        # 3. Check termination condition
        if self.crew.all_tasks_done():
            log("Kernel", "All tasks completed or failed. Simulation finished.")
            self.running = False
            return False # Stop simulation

        # Check for deadlock/stalled state (more relevant now with LLM delays/errors)
        if not running_tasks and not self.crew.get_tasks_by_state(TaskState.ASSIGNED):
             pending_ready = self.crew.get_tasks_by_state(TaskState.PENDING) + self.crew.get_tasks_by_state(TaskState.READY)
             if not pending_ready and not self.crew.all_tasks_done():
                 log("Kernel", "Warning: No tasks running/assigned, and no pending/ready tasks left, but not all tasks are done. Possible stall.")
             # Check if only pending tasks remain but no agents are available/running (less likely with idle agents)
             elif not self.crew.get_tasks_by_state(TaskState.READY) and self.crew.get_tasks_by_state(TaskState.PENDING) and not self.scheduler.get_available_agents() and not self.crew.get_agents_by_state(AgentState.RUNNING_TASK):
                  log("Kernel", "Warning: Tasks are PENDING, but no agents are IDLE or RUNNING. Possible deadlock.")


        return True # Continue simulation

    def run(self, max_ticks=50, delay=2.0): # Fewer ticks by default, longer delay
        """Runs the simulation loop."""
        if not self.crew:
            log("Kernel", "Cannot run. No crew loaded.")
            return
        log("Kernel", f"Starting simulation run (max_ticks={max_ticks}, delay={delay}s). Using Ollama model: {self.ollama_model}")
        self.running = True
        try:
            while self.tick_count < max_ticks:
                if not self.tick(): # tick returns False if simulation should stop
                    break
                log("Kernel", f"Pausing for {delay} seconds...")
                time.sleep(delay) # Pause for readability and to avoid hammering Ollama
        except KeyboardInterrupt:
             log("Kernel", "Simulation run interrupted by user (Ctrl+C).")
             self.running = False
        finally:
            if self.running: # Hit max_ticks?
                log("Kernel", f"Simulation stopped after reaching max_ticks ({max_ticks}).")
                self.running = False

            if self.resource_monitor:
                final_report = self.resource_monitor.get_report()
                log("Kernel", f"Final Resource Report: {final_report}")
            else:
                log("Kernel", "Resource monitor not available.")
