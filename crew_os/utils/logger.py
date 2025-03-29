import datetime
import os

# Simple logger
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}
CURRENT_LEVEL = LEVELS.get(LOG_LEVEL, 20)

def log(sender, message, level="INFO"):
    """Logs a message with timestamp and sender ID."""
    level_num = LEVELS.get(level.upper(), 20)
    if level_num >= CURRENT_LEVEL:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] [{level.upper():<7}] [{sender}]: {message}")

# Example Usage (can be removed from final file):
# log("Kernel", "Kernel initialized.", level="INFO")
# log("Agent", "Agent received task.", level="DEBUG") # Won't print by default
# log("ToolDispatcher", "Tool not found!", level="ERROR")
# os.environ["LOG_LEVEL"] = "DEBUG" # Set env var before running to see DEBUG logs
