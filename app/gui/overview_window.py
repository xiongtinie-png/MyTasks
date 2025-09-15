from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QDialogButtonBox, QMenu, QMessageBox
from PyQt6.QtCore import Qt, QPoint
from typing import Union, Optional
from ..data_manager import DataManager
from ..data_models import Task, TaskList, TaskStatus, TaskPriority
from .dialogs import TaskEditDialog
from datetime import datetime

class OverviewWindow(QDialog):
    def __init__(self, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.setWindowTitle("Task Lists Overview")
        self.setGeometry(150, 150, 800, 600)

        self.layout = QVBoxLayout(self)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["List / Task", "Status", "Priority", "Due Date"])
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.layout.addWidget(self.tree)

        # --- Buttons ---
        # Use a standard button box for robust closing behavior
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.button_box.rejected.connect(self.reject) # QDialog's standard close slot
        self.layout.addWidget(self.button_box)

        self.load_overview_data()

    def load_overview_data(self):
        self.tree.clear()
        all_task_lists = sorted(self.data_manager.get_all_task_lists(), key=lambda tl: tl.name)

        if not all_task_lists:
            self._add_empty_message("No task lists found.")
            return

        for task_list in all_task_lists:
            self._add_task_list_to_tree(task_list)

        self.tree.expandAll()
        for i in range(self.tree.columnCount()):
            self.tree.resizeColumnToContents(i)

    def _add_task_list_to_tree(self, task_list: TaskList):
        """Adds a task list and its tasks to the tree view."""
        list_item = QTreeWidgetItem(self.tree)
        list_item.setText(0, task_list.name)
        
        tasks = self.data_manager.get_tasks_for_task_list(task_list.id)
        
        if not tasks:
            self._add_empty_message("No tasks in this list.", parent=list_item)
        else:
            sorted_tasks = sorted(tasks, key=lambda t: (t.due_at or datetime.max, t.priority.value))
            for task in sorted_tasks:
                self._add_task_to_tree(list_item, task)

    def _add_task_to_tree(self, parent_item: QTreeWidgetItem, task: Task):
        """Adds a single task item to the tree under its parent list."""
        task_item = QTreeWidgetItem(parent_item)
        task_item.setText(0, task.description)
        task_item.setText(1, task.status.value)
        task_item.setText(2, task.priority.value)
        due_date_str = task.due_at.strftime('%Y-%m-%d %H:%M') if task.due_at else "N/A"
        task_item.setText(3, due_date_str)
        task_item.setData(0, Qt.ItemDataRole.UserRole, task)

    def _add_empty_message(self, text: str, parent: Optional[Union[QTreeWidget, QTreeWidgetItem]] = None):
        """Adds a disabled, informational item to the tree."""
        parent = parent or self.tree
        item = QTreeWidgetItem(parent)
        item.setText(0, text)
        item.setDisabled(True)

    def on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle double-clicking on a task to edit it."""
        task = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(task, Task):
            dialog = TaskEditDialog(task=task, data_manager=self.data_manager, parent=self)
            if dialog.exec():
                self.load_overview_data() # Refresh data in case of changes

    def show_context_menu(self, position: QPoint):
        """Shows a context menu for tasks in the overview."""
        item = self.tree.itemAt(position)
        if not item:
            return

        task = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(task, Task):
            return

        menu = QMenu()
        edit_action = menu.addAction("View/Edit Details")
        edit_action.triggered.connect(lambda: self.on_item_double_clicked(item, 0))
        menu.addSeparator()
        delete_action = menu.addAction("Delete Task")
        delete_action.triggered.connect(lambda: self.delete_task(task))
        
        menu.exec(self.tree.mapToGlobal(position))

    def delete_task(self, task: Task):
        """Asks for confirmation and deletes a task from the overview."""
        reply = QMessageBox.question(self, "Confirm Deletion",
                                     f"Are you sure you want to delete the task '{task.description}'?\n\n"
                                     "This action cannot be undone.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if self.data_manager.delete_task(task.id):
                self.load_overview_data() # Refresh the overview

    def showEvent(self, event):
        """Reload data when the window is shown."""
        self.load_overview_data()
        super().showEvent(event)
