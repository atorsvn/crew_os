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
