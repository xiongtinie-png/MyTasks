# c:\Users\xiongti\Documents\TeamTaskManager\app\gui\dialogs.py

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QDialogButtonBox, QLabel, QComboBox, QTextBrowser,
    QDateTimeEdit, QTextEdit, QFormLayout, QMessageBox, QListWidget, QPushButton,
    QHBoxLayout, QListWidgetItem
)
from PyQt6.QtCore import QDateTime, Qt
from ..data_manager import DataManager
from ..data_models import Task, TaskList, TaskStatus, TaskPriority, Comment
from datetime import datetime
import html
import re
from typing import Optional

class AddTaskListDialog(QDialog):
    """Dialog to add a new task list."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Task List")
        self.layout = QVBoxLayout(self)
        
        self.name_label = QLabel("Task List Name:")
        self.name_edit = QLineEdit()
        self.layout.addWidget(self.name_label)
        self.layout.addWidget(self.name_edit)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def get_name(self) -> str:
        """Get the entered name, stripped of whitespace."""
        return self.name_edit.text().strip()

    def accept(self):
        """Validate input before accepting."""
        if not self.get_name():
            QMessageBox.warning(self, "Input Error", "Task list name cannot be empty.")
            return
        super().accept()

class AddTaskDialog(QDialog):
    """Dialog to add a new task."""
    def __init__(self, task_list_id: str, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.task_list_id = task_list_id
        self.data_manager = data_manager
        
        self.setWindowTitle("Add New Task")
        self.setMinimumWidth(400)
        
        self.layout = QFormLayout(self)
        
        self.description_edit = QLineEdit()
        self.layout.addRow("Description:", self.description_edit)
        
        self.priority_combo = QComboBox()
        for priority in TaskPriority:
            self.priority_combo.addItem(priority.value, priority)
        self.layout.addRow("Priority:", self.priority_combo)
        
        self.start_at_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.start_at_edit.setCalendarPopup(True)
        self.layout.addRow("Start At:", self.start_at_edit)

        self.due_at_edit = QDateTimeEdit(QDateTime.currentDateTime().addDays(1))
        self.due_at_edit.setCalendarPopup(True)
        self.layout.addRow("Due At:", self.due_at_edit)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def accept(self):
        """Validate data and add the task."""
        description = self.description_edit.text().strip()
        if not description:
            QMessageBox.warning(self, "Input Error", "Task description cannot be empty.")
            return

        priority = self.priority_combo.currentData()
        start_at = self.start_at_edit.dateTime().toPyDateTime()
        due_at = self.due_at_edit.dateTime().toPyDateTime()

        if start_at >= due_at:
            QMessageBox.warning(self, "Input Error", "Start date must be before due date.")
            return

        new_task = self.data_manager.add_task(
            description=description,
            assigned_to_id=self.task_list_id,
            priority=priority,
            start_at=start_at,
            due_at=due_at
        )

        if new_task:
            super().accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to create the task. The assigned task list may no longer exist.")

class TaskDetailsDialog(QDialog):
    """Dialog to view and edit a task and its comments."""
    def __init__(self, task: Task, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.task = task
        self.data_manager = data_manager
        self.setWindowTitle("Task Details")
        self.setMinimumWidth(500)

        self.layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # --- Task Fields ---
        self.description_edit = QLineEdit(self.task.description)
        form_layout.addRow("Description:", self.description_edit)

        # Priority
        self.priority_combo = QComboBox()
        for priority in TaskPriority:
            self.priority_combo.addItem(priority.value, priority)
        current_prio_index = list(TaskPriority).index(self.task.priority)
        self.priority_combo.setCurrentIndex(current_prio_index)
        form_layout.addRow("Priority:", self.priority_combo)

        # Status
        self.status_combo = QComboBox()
        for status in TaskStatus:
            self.status_combo.addItem(status.value, status)
        self.status_combo.setCurrentIndex(list(TaskStatus).index(self.task.status))
        form_layout.addRow("Status:", self.status_combo)

        # Start At
        # Handle case where date might be None, which would cause a crash.
        start_dt = QDateTime(self.task.start_at) if self.task.start_at else QDateTime.currentDateTime()
        self.start_at_edit = QDateTimeEdit(start_dt)
        self.start_at_edit.setCalendarPopup(True)
        form_layout.addRow("Start At:", self.start_at_edit)

        # Due At
        # Handle case where date might be None, which would cause a crash.
        due_dt = QDateTime(self.task.due_at) if self.task.due_at else QDateTime.currentDateTime().addDays(1)
        self.due_at_edit = QDateTimeEdit(due_dt)
        self.due_at_edit.setCalendarPopup(True)
        form_layout.addRow("Due At:", self.due_at_edit)

        self.layout.addLayout(form_layout)

        # --- Comments Section ---
        self.layout.addWidget(QLabel("Comments:"))
        self.comments_browser = QTextBrowser()
        self.comments_browser.setOpenExternalLinks(True) # Open links in default browser
        self.layout.addWidget(self.comments_browser)
        self.load_comments()

        comment_layout = QHBoxLayout()
        self.comment_edit = QLineEdit()
        self.comment_edit.setPlaceholderText("Add a new comment...")
        self.add_comment_button = QPushButton("Add")
        self.add_comment_button.clicked.connect(self.add_comment)
        comment_layout.addWidget(self.comment_edit)
        comment_layout.addWidget(self.add_comment_button)
        self.layout.addLayout(comment_layout)

        # --- Dialog Buttons ---
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def load_comments(self):
        """Loads comments, finds URLs, and renders them as clickable links."""
        self.comments_browser.clear()
        html_parts = []

        # Regex to find URLs (http, https, or www).
        url_pattern = re.compile(r'((?:https?://|www\.)[^\s<]+)')

        for comment in self.task.comments:
            author_esc = html.escape(comment.author)

            # --- Linkification Process ---
            # Split the comment text by the URL pattern. This gives a list of [text, url, text, url, ...].
            text_parts = url_pattern.split(comment.text)
            linked_text_parts = []
            for i, part in enumerate(text_parts):
                if i % 2 == 1:  # This part is a URL
                    url = part
                    href = url if url.startswith(('http://', 'https://')) else f'http://{url}'
                    # The displayed text is escaped, while the href is used directly.
                    linked_text_parts.append(f'<a href="{href}">{html.escape(url)}</a>')
                else:  # This part is normal text, so we escape it.
                    linked_text_parts.append(html.escape(part))
            
            final_text = "".join(linked_text_parts).replace('\n', '<br>')
            # --- End Linkification ---

            html_parts.append(f"<b>{author_esc}</b> at {comment.timestamp.strftime('%Y-%m-%d %H:%M')}:<br>{final_text}<hr>")
        
        self.comments_browser.setHtml("".join(html_parts))

    def add_comment(self):
        """Adds a new comment to the task."""
        comment_text = self.comment_edit.text().strip()
        if not comment_text:
            return
        
        # In a real app, you'd get the author from a login system.
        # For now, we'll hardcode it.
        author = "CurrentUser"
        
        new_comment = Comment(
            author=author,
            text=comment_text,
            timestamp=datetime.now()
        )
        self.task.comments.append(new_comment)
        self.data_manager.update_task(self.task)
        self.load_comments()
        self.comment_edit.clear()

    def accept(self):
        """Saves changes to the task."""
        description = self.description_edit.text().strip()
        if not description:
            QMessageBox.warning(self, "Input Error", "Task description cannot be empty.")
            return

        start_at = self.start_at_edit.dateTime().toPyDateTime()
        due_at = self.due_at_edit.dateTime().toPyDateTime()

        if start_at >= due_at:
            QMessageBox.warning(self, "Input Error", "Start date must be before due date.")
            return

        # Update all task properties from the dialog fields
        self.task.description = self.description_edit.text().strip()
        self.task.status = self.status_combo.currentData()
        self.task.priority = self.priority_combo.currentData()
        self.task.start_at = self.start_at_edit.dateTime().toPyDateTime()
        self.task.due_at = self.due_at_edit.dateTime().toPyDateTime()
        
        self.data_manager.update_task(self.task)
        super().accept()
