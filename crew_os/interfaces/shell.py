from crew_os.core.kernel import Kernel
from crew_os.components.crew import Crew # For type hinting/creation
from crew_os.components.agent import Agent
from crew_os.components.task import Task
from crew_os.enums import CrewProcess # For creation
from crew_os.utils.logger import log
import time # For potential delays
import ollama # Need this to check models in shell

class Shell:
    def __init__(self, kernel: Kernel):
        self.kernel = kernel
        # No temporary storage needed here if sample crew is loaded directly

    def _print_status(self):
        if not self.kernel.crew:
            print("No crew loaded.")
            return

        print("\n--- Crew Status ---")
        print(f"Tick: {self.kernel.tick_count}")
        print(f"Process: {self.kernel.crew.process.name}")
        print(f"Ollama Model: {self.kernel.ollama_model}")
        print(f"Kernel Running: {self.kernel.running}")

        print("\nAgents:")
        if self.kernel.crew.agents:
            # Sort by AID for consistent display
            sorted_agents = sorted(self.kernel.crew.agents.values(), key=lambda a: a.aid)
            for agent in sorted_agents:
                print(f"  {agent}")
        else:
            print("  No agents in crew.")

        print("\nTasks:")
        if self.kernel.crew.tasks:
             # Sort by TID for consistent display
            sorted_tasks = sorted(self.kernel.crew.tasks.values(), key=lambda t: t.tid)
            for task in sorted_tasks:
                print(f"  {task}")
        else:
            print("  No tasks in crew.")

        # Check for potential issues
        if not self.kernel.running and self.kernel.crew and not self.kernel.crew.all_tasks_done():
            running_agents = any(a.state == AgentState.RUNNING_TASK for a in self.kernel.crew.agents.values())
            ready_tasks = any(t.state == TaskState.READY for t in self.kernel.crew.tasks.values())
            pending_tasks = any(t.state == TaskState.PENDING for t in self.kernel.crew.tasks.values())
            idle_agents = any(a.state == AgentState.IDLE for a in self.kernel.crew.agents.values())

            if not running_agents and not ready_tasks and pending_tasks:
                 print("\n[Status Hint: Simulation paused. Some tasks are PENDING dependencies.]")
            elif not running_agents and ready_tasks and not idle_agents:
                 print("\n[Status Hint: Simulation paused. Tasks are READY but no agents are IDLE.]")

        print("-------------------\n")


    def _create_sample_crew(self):
        """Helper to create a default crew for testing."""
        log("Shell", "Creating sample crew definition...")
        # Reset global counters for repeatable IDs in demos when loading sample
        Agent._next_aid = 0
        Task._next_tid = 0

        # Define Agents
        researcher = Agent(
            role="Market Researcher",
            goal="Find and summarize key AI market trends projected for 2025.",
            backstory="An expert analyst skilled in web research and data synthesis. Prefers concise summaries.",
            tools=["web_search"] # Only allowed tool
        )
        calculator_agent = Agent(
            role="Calculation Assistant",
            goal="Perform simple calculations based on provided data.",
            backstory="A straightforward assistant focused on numerical accuracy.",
            tools=["calculator"] # Only allowed tool
        )
        writer = Agent(
            role="Content Writer",
            goal="Write a brief 2-paragraph report based on research findings and calculations.",
            backstory="A skilled writer who synthesizes information clearly into reports.",
            tools=[] # No tools needed directly, uses context from others
        )


        # Define Tasks
        task1 = Task(
            description="Research AI market trends for 2025 using web search. Focus on 2-3 key trends.",
            expected_output="A bulleted list summarizing the key AI trends found.",
            agent_id=researcher.aid # Assign directly for simplicity in sample
        )
        task2 = Task(
            description="Calculate the potential market size increase if AI adoption grows by 15% from a base of $100 Billion. Use the calculator tool with the expression '100 * 1.15'.",
            expected_output="A single number representing the calculated market size in billions.",
            agent_id=calculator_agent.aid,
            dependencies=[] # Independent task for this example
        )
        task3 = Task(
            description="Write a 2-paragraph report summarizing the AI trends from Task 0 and including the market size calculation from Task 1.",
            expected_output="A formatted text report incorporating information from task dependencies.",
            agent_id=writer.aid,
            dependencies=[task1.tid, task2.tid] # Depends on task1 (TID 0) and task2 (TID 1)
        )


        sample_agents = [researcher, calculator_agent, writer]
        sample_tasks = [task1, task2, task3]

        # Create and load the crew
        crew = Crew(
            agents=sample_agents,
            tasks=sample_tasks,
            process=CrewProcess.SEQUENTIAL # Tasks run based on dependency graph and queue order
        )
        self.kernel.load_crew(crew)
        log("Shell", "Sample crew loaded into kernel.")

    def start(self):
        print("\nWelcome to CrewOS Shell (Ollama Integrated)!")
        print("Ensure Ollama is running and the model is available.")
        print(f"Using Ollama model: {self.kernel.ollama_model}")
        print("Type 'help' for commands.")

        while True:
            try:
                # Auto-status update can be noisy if running fast, prompt when idle
                if self.kernel.running:
                     # Maybe print minimal status update or just wait?
                     # print(f"Tick: {self.kernel.tick_count}...") # Example minimal status
                     time.sleep(0.1) # Short sleep to prevent busy-waiting CPU usage
                     continue # Loop back to check if still running

                # Prompt for input only when kernel is not running
                command_input = input("CrewOS> ").strip().lower()
                if not command_input:
                    continue

                command_parts = command_input.split()
                cmd = command_parts[0]
                args = command_parts[1:]


                if cmd == "exit":
                    if self.kernel.running:
                         print("Stopping simulation...")
                         self.kernel.running = False # Attempt to stop cleanly
                    print("Exiting CrewOS Shell.")
                    break
                elif cmd == "help":
                    print("\nAvailable Commands:")
                    print("  load_sample    - Load a predefined sample crew.")
                    # print("  load <file>    - Load crew definition from file (Not Implemented).")
                    print("  start [ticks]  - Start simulation (runs up to N ticks, default 50).")
                    print("  tick           - Advance simulation by one tick.")
                    print("  status         - Show current status of agents and tasks.")
                    print("  report         - Show resource usage report.")
                    print("  model [name]   - Show/Set Ollama model (e.g., 'model llama3'). Requires reload.")
                    print("  help           - Show this help message.")
                    print("  exit           - Exit the shell.")
                elif cmd == "load_sample":
                     if self.kernel.running:
                         print("Cannot load while simulation is running. Stop first.")
                     else:
                         self._create_sample_crew()
                         self._print_status()
                elif cmd == "start":
                     if not self.kernel.crew:
                         print("No crew loaded. Use 'load_sample' first.")
                         continue
                     if self.kernel.running:
                         print("Simulation is already running.")
                         continue

                     try:
                         # Use default from kernel.run if no arg provided
                         ticks = int(args[0]) if args and args[0].isdigit() else 50
                         # Use default delay from kernel.run
                         self.kernel.run(max_ticks=ticks)
                     except Exception as e:
                          log("Shell", f"Error during simulation run: {e}")
                          self.kernel.running = False # Ensure kernel stops on error

                     # Show status after run finishes or stops
                     self._print_status()
                elif cmd == "tick":
                    if not self.kernel.crew:
                         print("No crew loaded. Use 'load_sample' first.")
                         continue
                    if self.kernel.running:
                         print("Simulation is already running automatically via 'start'. Use Ctrl+C to interrupt.")
                         continue

                    # Execute a single tick
                    self.kernel.running = True # Allow one tick
                    try:
                        self.kernel.tick()
                    except Exception as e:
                         log("Shell", f"Error during single tick execution: {e}")
                    finally:
                        self.kernel.running = False # Stop after one tick regardless of outcome
                    self._print_status()


                elif cmd == "status":
                    self._print_status()
                elif cmd == "report":
                    if self.kernel.resource_monitor:
                         report = self.kernel.resource_monitor.get_report()
                         print("\n--- Resource Report ---")
                         print(f"  Total Tokens (Estimate): {report.get('total_tokens', 0)}")
                         print(f"  Total Tool Calls: {report.get('total_tool_calls', 0)}")
                         print("-----------------------\n")
                    else:
                         print("No resource monitor available (load a crew first).")

                elif cmd == "model":
                     if self.kernel.running:
                         print("Cannot change model while simulation is running.")
                     elif args:
                         new_model = args[0]
                         # Basic validation - could improve
                         if not new_model:
                              print("Error: No model name provided.")
                              continue
                         self.kernel.ollama_model = new_model
                         print(f"Ollama model set to '{new_model}'.")
                         # Re-check availability?
                         try:
                            log("Shell", f"Checking availability of model '{new_model}'...")
                            available_models = ollama.list().get('models', [])
                            model_found = any(m['name'].startswith(new_model) for m in available_models)
                            if not model_found:
                                log("Shell", f"Warning: Model '{new_model}' not found in local Ollama models. Please ensure it is pulled (`ollama pull {new_model}`).")
                            else:
                                log("Shell", f"Model '{new_model}' appears available.")
                         except Exception as e:
                            log("Shell", f"Could not check Ollama models: {e}")

                     else:
                         print(f"Current Ollama model: {self.kernel.ollama_model}")


                else:
                    print(f"Unknown command: {cmd}. Type 'help' for options.")

            except EOFError: # Handle Ctrl+D
                 print("\nExiting CrewOS Shell.")
                 if self.kernel: self.kernel.running = False
                 break
            except KeyboardInterrupt: # Handle Ctrl+C during input or idle
                 print("\nOperation interrupted. Type 'exit' to quit.")
                 if self.kernel: self.kernel.running = False # Ensure simulation stops if it was running
            except Exception as e:
                log("Shell", f"An unexpected error occurred in the shell: {type(e).__name__} - {e}")
                import traceback
                traceback.print_exc() # Print full traceback for debugging shell issues
                if self.kernel: self.kernel.running = False # Stop simulation on error
