from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTreeWidget,
                             QPushButton, QCalendarWidget, QTreeWidgetItem, QMenu, QMessageBox)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor
from ..data_manager import DataManager
from ..data_models import TaskList, Task, TaskStatus, TaskPriority, Comment
from .dialogs import AddTaskDialog, TaskDetailsDialog
from datetime import date as py_date, datetime
from typing import Optional
import re
import html

class DailyTodoWidget(QWidget):
    _PRIORITY_COLORS = {
        TaskPriority.HIGH: QColor("#E57373"),    # Softer red
        TaskPriority.MEDIUM: QColor("#FFB74D"),   # Softer orange
        TaskPriority.LOW: QColor("#81C784"),     # Softer green
    }

    def __init__(self, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.current_task_list: Optional[TaskList] = None
        self.current_task_lists: Optional[list[TaskList]] = None # For combined view
        self.current_date: QDate = QDate.currentDate()

        self.layout = QVBoxLayout(self)

        self.title_label = QLabel("No task list selected")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.layout.addWidget(self.title_label)

        # Calendar
        self.calendar = QCalendarWidget()
        self.calendar.setSelectedDate(self.current_date)
        self.calendar.clicked.connect(self.on_date_changed)
        self.calendar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.calendar.customContextMenuRequested.connect(self.show_calendar_context_menu)
        self.layout.addWidget(self.calendar)

        # Tasks list
        self.tasks_list_widget = QTreeWidget()
        self.tasks_list_widget.setHeaderHidden(True)
        self.tasks_list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tasks_list_widget.customContextMenuRequested.connect(self.show_task_context_menu)
        self.tasks_list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.layout.addWidget(self.tasks_list_widget)

        # Add Task Button
        self.add_task_button = QPushButton("Add New Task")
        self.add_task_button.clicked.connect(self.add_new_task)
        self.layout.addWidget(self.add_task_button)

        # Initially hide widgets that depend on a task list being selected
        self.show_placeholder_message("Select a workspace from the 'Team' menu to begin.")

        self.setLayout(self.layout)

    def on_date_changed(self, date: QDate):
        self.current_date = date
        if self.current_task_list:
            self.title_label.setText(f"Tasks for {self.current_task_list.name} on {self.current_date.toString('yyyy-MM-dd')}")
        self.load_tasks()

    def set_task_list_and_date(self, task_list: TaskList, date: py_date):
        """Sets the view for a single task list."""
        self.current_task_list = task_list
        self.current_task_lists = None # Clear the multi-list view

        self.calendar.setVisible(True)
        self.add_task_button.setVisible(True)
        self.add_task_button.setEnabled(True)

        self.current_date = QDate(date)
        self.calendar.setSelectedDate(self.current_date)
        self.title_label.setText(f"Tasks for {self.current_task_list.name} on {self.current_date.toString('yyyy-MM-dd')}")
        self.load_tasks()

    def show_placeholder_message(self, text: str):
        self.current_task_list = None
        self.title_label.setText(text)
        self.tasks_list_widget.clear()
        self.calendar.setVisible(False)
        self.add_task_button.setVisible(False)

    def load_tasks(self):
        self.tasks_list_widget.clear()
        py_target_date = self.current_date.toPyDate()
        tasks_for_day = []

        if self.current_task_list:
            all_tasks = self.data_manager.get_tasks_for_task_list(self.current_task_list.id)
            tasks_for_day = [task for task in all_tasks if self._is_task_for_date(task, py_target_date)]
        else:
            return

        if not tasks_for_day:
            empty_item = QTreeWidgetItem(self.tasks_list_widget)
            empty_item.setText(0, "No tasks for this day.")
            empty_item.setDisabled(True)
            return

        tasks_for_day.sort(key=lambda t: (t.priority.value, t.due_at or datetime.max))

        for task in tasks_for_day:
            # Create the top-level item for the task
            task_item = self._create_task_tree_item(task)
            self.tasks_list_widget.addTopLevelItem(task_item)

            # Create child items for each comment
            if task.comments:
                for comment in task.comments:
                    # Create a basic tree item to hold the data and widget
                    comment_item = QTreeWidgetItem()
                    comment_item.setData(0, Qt.ItemDataRole.UserRole, comment)
                    task_item.addChild(comment_item)

                    # Create and set the custom widget for the comment
                    comment_widget = self._create_comment_widget(comment)
                    self.tasks_list_widget.setItemWidget(comment_item, 0, comment_widget)
                # Expand the task item to show comments by default
                task_item.setExpanded(True)

    def _is_task_for_date(self, task: Task, target_date: py_date) -> bool:
        start_date = task.start_at.date() if task.start_at else None
        due_date = task.due_at.date() if task.due_at else None

        if start_date and due_date:
            return start_date <= target_date <= due_date
        if due_date:
            return due_date == target_date
        return False

    def _create_task_tree_item(self, task: Task) -> QTreeWidgetItem:
        item_text = self._format_task_item_text(task)
        task_item = QTreeWidgetItem()
        task_item.setText(0, item_text)

        if task.status == TaskStatus.QUESTION:
            task_item.setForeground(0, QColor("magenta"))
        elif task.priority in self._PRIORITY_COLORS:
            task_item.setForeground(0, self._PRIORITY_COLORS[task.priority])

        task_item.setData(0, Qt.ItemDataRole.UserRole, task)
        return task_item

    def _create_comment_widget(self, comment: Comment) -> QWidget:
        """Creates a QLabel with rich text for displaying a comment with clickable links."""
        # --- Linkification Process (similar to TaskDetailsDialog) ---
        url_pattern = re.compile(r'((?:https?://|www\.)[^\s<]+)')
        text_parts = url_pattern.split(comment.text)
        linked_text_parts = []
        for i, part in enumerate(text_parts):
            if i % 2 == 1:  # This part is a URL
                url = part
                href = url if url.startswith(('http://', 'https://')) else f'http://{url}'
                linked_text_parts.append(f'<a href="{href}">{html.escape(url)}</a>')
            else:  # This part is normal text
                linked_text_parts.append(html.escape(part))
        
        final_text = "".join(linked_text_parts).replace('\n', '<br>')
        # --- End Linkification ---

        # Use a QLabel to render the HTML content.
        # The `└─ ` prefix gives a visual cue of hierarchy.
        comment_label = QLabel(f"└─ {final_text}")
        comment_label.setWordWrap(True)
        comment_label.setOpenExternalLinks(True)
        # Make comments visually distinct and ensure background is transparent for correct themeing.
        comment_label.setStyleSheet("color: gray; background-color: transparent;")
        
        return comment_label

    def _format_task_item_text(self, task: Task) -> str:
        date_text = ""
        if task.start_at and task.due_at:
            if task.start_at.date() == task.due_at.date():
                date_text = f" ({task.start_at.strftime('%H:%M')} - {task.due_at.strftime('%H:%M')})"
            else:
                date_text = f" ({task.start_at.strftime('%b %d')} - {task.due_at.strftime('%b %d')})"
        elif task.due_at:
            date_text = f" (Due: {task.due_at.strftime('%b %d %H:%M')})"

        return f"{task.status.value} - {task.description}{date_text}"

    def add_new_task(self):
        if not self.current_task_list:
            QMessageBox.warning(self, "Cannot Add Task", "Please select a list from the panel on the left.")
            return
        
        dialog = AddTaskDialog(self.current_task_list.id, self.data_manager, self)
        if dialog.exec():
            self.load_tasks()

    def show_calendar_context_menu(self, position):
        """Shows a context menu on the calendar to add a task for the selected date."""
        if not self.current_task_list:
            # Don't show a menu if no task list is active
            return

        menu = QMenu(self)
        add_task_action = menu.addAction(f"Add New Task for {self.current_date.toString('yyyy-MM-dd')}...")
        add_task_action.triggered.connect(self.add_new_task)
        menu.exec(self.calendar.mapToGlobal(position))

    def on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """
        Handles double-clicks. If it's a task item, show details.
        If it's a comment, do nothing for now.
        """
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, Task):
            self.show_task_details(item)

    def show_task_details(self, item: QTreeWidgetItem):
        task = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(task, Task):
            return
        
        dialog = TaskDetailsDialog(task, self.data_manager, self)
        if dialog.exec():
            self.load_tasks()

    def show_task_context_menu(self, position):
        item = self.tasks_list_widget.itemAt(position)
        if not item:
            return
        
        task = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(task, Task):
            # This is a comment or other non-task item, so don't show a context menu.
            return

        menu = QMenu()
        
        details_action = menu.addAction("View/Edit Details & Comments")
        details_action.triggered.connect(lambda: self.show_task_details(item))
        menu.addSeparator()

        priority_menu = menu.addMenu("Set Priority")
        for prio in TaskPriority:
            prio_action = priority_menu.addAction(f"{prio.value}")
            prio_action.triggered.connect(lambda checked=False, p=prio, t=task: self.change_task_priority(t, p))
        menu.addSeparator()

        status_menu = menu.addMenu("Mark as")
        for status in TaskStatus:
            action = status_menu.addAction(f"{status.value}")
            action.triggered.connect(lambda checked=False, s=status, t=task: self.change_task_status(t, s))

        menu.exec(self.tasks_list_widget.mapToGlobal(position))

    def change_task_priority(self, task: Task, new_priority: TaskPriority):
        task.priority = new_priority
        self.data_manager.update_task(task)
        self.load_tasks()

    def change_task_status(self, task: Task, new_status: TaskStatus):
        task.status = new_status
        self.data_manager.update_task(task)
        self.load_tasks()