# CrewOS Simulation (with Ollama Integration)

This project simulates a conceptual "Crew Operating System" (CrewOS) designed to orchestrate AI agents working collaboratively on tasks. This version replaces the purely random simulation logic with actual calls to a local LLM via the `ollama` library, allowing agents to "think" and decide actions based on prompts.

## Features

* **Agent & Task Management:** Define agents with roles, goals, backstories, and permitted tools. Define tasks with descriptions, dependencies, and expected outputs.
* **Sequential Process:** Implements a sequential workflow where tasks are queued and executed based on dependencies and agent availability.
* **Ollama Integration:** Agent decision-making (choosing actions like using a tool or providing a final answer) is driven by calls to a configured Ollama model.
* **Tool Dispatcher:** Agents can request to use tools (e.g., `web_search`, `calculator`). The dispatcher validates authorization and executes the tool (currently simulated tool logic).
* **Resource Monitoring (Simulated):** Tracks estimated token usage (based on LLM calls and tool costs) and tool calls.
* **Command-Line Interface (CLI):** An interactive shell (`main.py`) allows loading a sample crew, stepping through ticks, running the simulation automatically, and checking status/reports.

## Directory Structure

```
crew_os_project/
├── crew_os/            # Main package source code
│   ├── core/           # Kernel, Scheduler, Managers
│   ├── components/     # Agent, Task, Tool, Crew definitions
│   ├── interfaces/     # Shell UI
│   ├── utils/          # Logger
│   └── enums.py        # State definitions
├── main.py             # Main entry point to start the shell
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

## Requirements

* **Python:** 3.9 or higher recommended.
* **Ollama:** A running instance of [Ollama](https://ollama.com/).
* **Ollama Model:** An appropriate Ollama model pulled (e.g., `llama3`, `mistral`). The default configured in `kernel.py` is `llama3`. Ensure the model is suitable for following JSON formatting instructions.
* **Python Libraries:** See `requirements.txt`. Install using pip:
    ```bash
    pip install -r requirements.txt
    ```

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd crew_os_project
    ```
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Install and Run Ollama:**
    * Follow the instructions on [ollama.com](https://ollama.com/) to install Ollama for your operating system.
    * Start the Ollama application or run `ollama serve` in your terminal.
    * Pull the desired model (default is `llama3`):
        ```bash
        ollama pull llama3
        ```
        *(Replace `llama3` if you configure a different model in `kernel.py` or via the shell)*

## Running the Simulation

1.  Ensure your Ollama instance is running.
2.  Navigate to the `crew_os_project` directory in your terminal.
3.  Run the main script:
    ```bash
    python main.py
    ```

## Using the Shell

You will be greeted by the `CrewOS>` prompt. Available commands:

* `help`: Show available commands.
* `load_sample`: Loads a predefined crew with agents (Researcher, Calculator, Writer) and tasks. Resets previous state.
* `status`: Display the current tick, agent states, task states, and resource usage.
* `tick`: Advance the simulation by a single step (tick). This involves LLM calls and can be slow.
* `start [N]`: Run the simulation automatically for up to `N` ticks (default: 50, see `kernel.run`). Use Ctrl+C to interrupt.
* `report`: Show the final resource usage report (estimated tokens, tool calls).
* `model [name]`: Show the currently configured Ollama model. If `[name]` is provided, sets the model for subsequent LLM calls (requires reloading the crew if kernel init depends on it).
* `exit`: Stop the simulation (if running) and exit the shell.

## How It Works

1.  **Loading:** `load_sample` creates `Agent` and `Task` objects and loads them into the `Kernel`.
2.  **Scheduling:** The `Scheduler` (in `SEQUENTIAL` mode) checks task dependencies (`TaskManager`) and assigns `READY` tasks from a queue to `IDLE` agents. It transitions `ASSIGNED` tasks to `RUNNING`.
3.  **Execution Tick (`Kernel.tick`):**
    * The `Kernel` identifies tasks in the `RUNNING` state.
    * For each `RUNNING` task, `_simulate_agent_work` is called.
    * `_simulate_agent_work`:
        * Builds a prompt including agent details, task info, context, and available tools using `_build_llm_prompt`.
        * Instructs the LLM to respond with JSON (`{"action": "use_tool", ...}` or `{"action": "final_answer", ...}`).
        * Calls the configured Ollama model via `_call_ollama`.
        * Parses the JSON response.
        * If `use_tool`: Calls `ToolDispatcher`, gets the result, and *calls the LLM again* with the tool result included in the prompt.
        * If `final_answer`: Updates the task state to `COMPLETED`, saves the result, and releases the agent (`IDLE`).
4.  **Looping:** The `start` command repeatedly calls `tick` with a delay until all tasks are done or `max_ticks` is reached.

## Configuration

* **Ollama Model:** The default model (`llama3`) is set in `crew_os/core/kernel.py`. You can change it there or using the `model <name>` command in the shell.
* **LLM Parameters:** Temperature and other Ollama settings can be adjusted within `_call_ollama` in `kernel.py`.
* **Simulation Speed:** The `delay` between ticks in `kernel.run` can be adjusted.

## Limitations

* **Prompt Engineering:** The system heavily relies on the LLM correctly interpreting the prompt and adhering *strictly* to the requested JSON format. This can be brittle.
* **Error Handling:** Basic error handling for Ollama API calls and JSON parsing exists, but complex failures (e.g., nonsensical LLM responses) might stall agents.
* **Synchronous Tools:** Tool execution is currently synchronous. The agent waits for the tool result before proceeding.
* **Basic Simulation:** Tool logic is simulated. Resource monitoring (tokens) is an estimate.
* **Sequential Only:** Only the sequential process is implemented.

## Future Work Ideas

* Implement Hierarchical or Parallel crew processes.
* Improve LLM interaction robustness (retries, format correction prompts).
* Implement asynchronous tool execution and LLM calls.
* Add more sophisticated agent capabilities (memory, delegation).
* Load/Save crew definitions from/to files (YAML/JSON).
* Develop a graphical user interface (GUI).
* Integrate actual tool APIs instead of simulations.
* More detailed and accurate resource tracking.
