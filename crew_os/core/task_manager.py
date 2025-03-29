from crew_os.enums import TaskState
from crew_os.components.task import Task
from crew_os.utils.logger import log

class TaskManager:
    def __init__(self, tasks: dict[int, Task]):
        self._tasks = tasks # Reference to the crew's tasks dictionary

    def get_task(self, tid: int) -> Task | None:
        return self._tasks.get(tid)

    def update_task_state(self, tid: int, new_state: TaskState):
        task = self.get_task(tid)
        if task:
            if task.state != new_state:
                 log("TaskManager", f"Updating Task {tid} state from {task.state.name} to {new_state.name}")
                 task.update_state(new_state)
            # else: log only if needed: log("TaskManager", f"Task {tid} state already {new_state.name}")
        else:
            log("TaskManager", f"Error: Cannot update state for unknown Task {tid}")

    def add_result(self, tid: int, result: str):
        task = self.get_task(tid)
        if task:
            task.add_result(result)
            log("TaskManager", f"Result added for Task {tid}")
        else:
            log("TaskManager", f"Error: Cannot add result for unknown Task {tid}")

    def build_context(self, task: Task) -> str:
        """Builds context string from dependencies' results."""
        if not task.dependencies:
            log("TaskManager", f"Task {task.tid} has no dependencies, context is empty.")
            task.add_context("") # Ensure context is explicitly empty
            return ""

        context_parts = []
        all_deps_completed = True
        log("TaskManager", f"Building context for Task {task.tid} from dependencies: {task.dependencies}")
        for dep_tid in task.dependencies:
            dep_task = self.get_task(dep_tid)
            if dep_task and dep_task.state == TaskState.COMPLETED and dep_task.result is not None:
                log("TaskManager", f"Adding result from completed dependency Task {dep_tid} to context of Task {task.tid}.")
                context_parts.append(f"--- Output from Task {dep_tid} ({dep_task.description[:30]}...) ---\n{dep_task.result}\n--- End Task {dep_tid} ---")
            else:
                status = f"State: {dep_task.state.name}" if dep_task else "Not Found"
                log("TaskManager", f"Dependency Task {dep_tid} for Task {task.tid} not completed ({status}). Cannot build full context yet.")
                all_deps_completed = False
                break # Don't add partial context if strict dependency required

        if all_deps_completed:
            full_context = "\n\n".join(context_parts)
            task.add_context(full_context)
            log("TaskManager", f"Successfully built context for Task {task.tid}.")
            return full_context
        else:
            # This case should ideally not happen if READY state is set correctly,
            # but log a warning if context is built prematurely.
            log("TaskManager", f"Warning: Failed to build full context for Task {task.tid}, dependencies not met.")
            task.add_context(None) # Ensure context is None if incomplete
            return ""

    def check_and_update_task_readiness(self):
        """Iterates through PENDING tasks and marks them READY if dependencies are met."""
        made_ready_count = 0
        for task in self._tasks.values():
            if task.state == TaskState.PENDING:
                deps_met = True
                if task.dependencies:
                    for dep_tid in task.dependencies:
                        dep_task = self.get_task(dep_tid)
                        # Check if dependency exists and is completed
                        if not dep_task or dep_task.state != TaskState.COMPLETED:
                            deps_met = False
                            break
                if deps_met:
                    self.update_task_state(task.tid, TaskState.READY)
                    made_ready_count += 1
        if made_ready_count > 0:
            log("TaskManager", f"Marked {made_ready_count} tasks as READY.")
