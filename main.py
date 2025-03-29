# Ensure the crew_os package is discoverable
import sys
import os
# Add project root to path if necessary (e.g., running from IDE)
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import necessary modules only after potentially modifying path
try:
    from crew_os.core.kernel import Kernel
    from crew_os.interfaces.shell import Shell
    from crew_os.utils.logger import log # Use the logger
except ImportError as e:
     print(f"Error importing CrewOS modules: {e}")
     print("Ensure the script is run from the 'crew_os_project' directory,")
     print("or that the project directory is in your PYTHONPATH.")
     sys.exit(1)
except Exception as e:
     print(f"An unexpected error occurred during import: {e}")
     sys.exit(1)


if __name__ == "__main__":
    log("Main", "Initializing CrewOS Kernel...")
    # You could potentially pass a model name here if desired via command line args
    # e.g., model = sys.argv[1] if len(sys.argv) > 1 else "llama3"
    # kernel = Kernel(ollama_model=model)
    try:
        kernel = Kernel() # Uses default model specified in Kernel.__init__
        log("Main", "Starting CrewOS Shell...")
        shell = Shell(kernel)
        shell.start() # Enters the main loop
    except Exception as e:
         log("Main", f"Critical error during initialization or shell execution: {e}", level="ERROR")
         import traceback
         traceback.print_exc() # Print traceback for critical errors
    finally:
        log("Main", "CrewOS Simulation Ended.")
