# c:\Users\xiongti\Documents\TeamTaskManager\app\data_manager.py
import os
import json
import sys # Import sys to check if running as a bundled app
from datetime import datetime, date
from typing import List, Dict, Optional
from .data_models import TaskList, Task, TaskStatus, Comment, TaskPriority
# from .utils import DATE_FORMAT # Currently not used in this file

class DataManager:
    def __init__(self, data_folder_name="data"):
        # Determine the base directory for data storage.
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # Running in a PyInstaller bundle (frozen)
            # sys.executable is the path to the .exe
            # We want the data folder to be in the same directory as the .exe
            self.base_dir = os.path.dirname(sys.executable)
        else:
            # Running as a normal Python script
            # Assume data_manager.py is in 'app' folder,
            # and we want the 'data' folder in the project root (one level up from 'app').
            script_dir = os.path.dirname(os.path.abspath(__file__))
            self.base_dir = os.path.abspath(os.path.join(script_dir, os.pardir))

        self.data_dir = os.path.join(self.base_dir, data_folder_name)
        self.members_file = os.path.join(self.data_dir, "task_lists.json") # Using plural version
        self.tasks_file = os.path.join(self.data_dir, "tasks.json")       # Using plural version
        os.makedirs(self.data_dir, exist_ok=True)


        self.task_lists: Dict[str, TaskList] = {}
        self.tasks: Dict[str, Task] = {}
        # self.load_data() # load_data is called from main.py after DataManager instantiation

    def _load_json(self, file_path: str) -> list:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                return data if isinstance(data, list) else [] # Ensure it's a list
        except FileNotFoundError:
            print(f"Info: File {file_path} not found. Will be created on save.")
            return []
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {file_path}. Returning empty list.")
            return []
        except Exception as e:
            print(f"An unexpected error occurred while loading {file_path}: {e}")
            return []


    def _save_json(self, file_path: str, data: list):
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)
            print(f"Data successfully saved to {file_path}")
        except IOError as e:
            print(f"IOError: Could not write to file {file_path}. Error: {e}")
        except TypeError as e:
            print(f"TypeError: Could not serialize data to JSON for {file_path}. Error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred while saving to {file_path}. Error: {e}")

    def load_data(self):
        self.task_lists.clear()
        self.tasks.clear()
        # Load Task Lists
        task_lists_data = self._load_json(self.members_file)
        for list_dict in task_lists_data:
            # Ensure id and name exist, otherwise skip this malformed entry
            if 'id' not in list_dict or 'name' not in list_dict:
                print(f"Warning: Skipping malformed task list entry in {self.members_file}: {list_dict}")
                continue
            task_list = TaskList(id=list_dict['id'], name=list_dict['name'])
            self.task_lists[task_list.id] = task_list

        # Load Tasks
        tasks_data = self._load_json(self.tasks_file)
        for task_dict in tasks_data:
            comments = [Comment.from_dict(c) for c in task_dict.get('comments', [])]
            task = Task(
                id=task_dict['id'],
                description=task_dict['description'],
                status=TaskStatus[task_dict.get('status', TaskStatus.PENDING.name).upper()],
                comments=comments,
                priority=TaskPriority[task_dict.get('priority', TaskPriority.MEDIUM.name).upper()],
                created_at=datetime.fromisoformat(task_dict.get('created_at', datetime.now().isoformat())),
                assigned_to=task_dict.get('assigned_to')
            ) # due_at will be None if not present in old data
            task.start_at = datetime.fromisoformat(task_dict['start_at']) if task_dict.get('start_at') else None
            task.due_at = datetime.fromisoformat(task_dict['due_at']) if task_dict.get('due_at') else None
            self.tasks[task.id] = task
        print("Data loaded.")
        if not task_lists_data and not tasks_data:
            print(f"Note: Both {self.members_file} and {self.tasks_file} were empty or not found. New files will be created on save if data is added.")

    def save_data(self):
        # Save Task Lists
        task_lists_list = [{"id": m.id, "name": m.name} for m in self.task_lists.values()]
        self._save_json(self.members_file, task_lists_list)

        # Save Tasks
        tasks_list = []
        for task in self.tasks.values():
            task_dict = {
                "id": task.id,
                "description": task.description,
                "status": task.status.name, # Store enum name
                "priority": task.priority.name, # Store enum name
                "comments": [c.to_dict() for c in task.comments],
                "created_at": task.created_at.isoformat(),
                "start_at": task.start_at.isoformat() if task.start_at else None,
                "due_at": task.due_at.isoformat() if task.due_at else None, # Save due_at
                "assigned_to": task.assigned_to
            }
            tasks_list.append(task_dict)
        self._save_json(self.tasks_file, tasks_list) # Ensure this uses self.tasks_file

    # --- TaskList Operations ---
    def add_task_list(self, name: str) -> Optional[TaskList]:
        if any(task_list.name.lower() == name.lower() for task_list in self.task_lists.values()):
            print(f"Task List '{name}' already exists.")
            return None
        new_list = TaskList(name=name)
        self.task_lists[new_list.id] = new_list
        self.save_data() # Ensure save is called
        return new_list

    def get_task_list_by_id(self, list_id: str) -> Optional[TaskList]:
        return self.task_lists.get(list_id)

    def get_all_task_lists(self) -> List[TaskList]:
        return list(self.task_lists.values())

    def update_task_list(self, task_list: TaskList):
        if task_list.id in self.task_lists:
            self.task_lists[task_list.id] = task_list
            self.save_data() # Ensure save is called
        else:
            print(f"Error: Task List with ID '{task_list.id}' not found for update.")

    def update_task_list_name(self, list_id: str, new_name: str) -> bool:
        """Updates the name of a task list, ensuring the new name is unique."""
        # Check if another task list with the new name already exists.
        if any(tl.name.lower() == new_name.lower() and tl.id != list_id for tl in self.task_lists.values()):
            print(f"Error: A task list with the name '{new_name}' already exists.")
            return False
        
        task_list = self.get_task_list_by_id(list_id)
        if task_list:
            task_list.name = new_name
            self.save_data() # Save the changes
            return True
        
        print(f"Error: Task List with ID '{list_id}' not found for rename.")
        return False

    def delete_task_list(self, list_id: str) -> bool:
        if list_id in self.task_lists:
            del self.task_lists[list_id]
            # Handle tasks assigned to the deleted member:
            # Option 1: Unassign tasks
            tasks_to_update = []
            for task_id, task in self.tasks.items():
                if task.assigned_to == list_id:
                    task.assigned_to = None # Unassign
                    tasks_to_update.append(task)
            for task in tasks_to_update:
                self.update_task(task) # This will also save
            self.save_data() # Save after member deletion and task updates
            return True
        return False

    # --- Task Operations ---
    def add_task(self, description: str, assigned_to_id: str,
                 priority: TaskPriority = TaskPriority.MEDIUM, status: TaskStatus = TaskStatus.PENDING,
                 start_at: Optional[datetime] = None, due_at: Optional[datetime] = None) -> Optional[Task]:
        if assigned_to_id not in self.task_lists:
            print(f"Error: Task List with ID '{assigned_to_id}' not found.")
            return None
        task = Task(
            description=description,
            assigned_to=assigned_to_id,
            priority=priority,
            status=status,
            start_at=start_at,
            due_at=due_at
        )
        self.tasks[task.id] = task # Add to the dictionary
        self.save_data() # Save immediately after adding a task
        return task

    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)

    def get_tasks_for_task_list(self, list_id: str) -> List[Task]:
        return [task for task in self.tasks.values() if task.assigned_to == list_id]

    def get_tasks_for_task_list_on_date(self, list_id: str, target_date: date) -> List[Task]:
        member_tasks = []
        for task in self.tasks.values():
            if task.assigned_to != list_id:
                continue
            
            start_at = getattr(task, 'start_at', None)
            due_at = task.due_at
            if start_at and due_at:
                if start_at.date() <= target_date <= due_at.date():
                    member_tasks.append(task)
            elif due_at and due_at.date() == target_date:
                member_tasks.append(task)
        return sorted(member_tasks, key=lambda t: t.created_at) # Sort by creation time

    def update_task(self, task: Task): # Takes a Task object
        if task and task.id in self.tasks:
            self.tasks[task.id] = task # Replace the whole task object
            self.save_data() # Ensure save is called
        else:
            print(f"Error: Task with ID '{task.id}' not found for update.")

    def add_comment_to_task(self, task_id: str, comment_text: str, author_name: str) -> bool:
        task = self.get_task_by_id(task_id)
        if task:
            comment = Comment(text=comment_text, author=author_name)
            task.comments.append(comment)
            self.save_data() # Ensure save is called
            return True
        return False
