# c:\Users\xiongti\Documents\TeamTaskManager\app\gui\dialogs.py

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QDialogButtonBox, QLabel, QComboBox, QTextBrowser,
    QDateTimeEdit, QTextEdit, QFormLayout, QMessageBox, QListWidget, QPushButton, QHBoxLayout,
    QListWidgetItem, QMenu, QInputDialog, QWidget, QFileDialog
)
from PyQt6.QtCore import QDateTime, Qt
from ..data_manager import DataManager
from ..data_models import Task, TaskList, TaskStatus, TaskPriority, Comment
from datetime import datetime
import html
import re
import os
import shutil
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
        self.description_edit.setStyleSheet("""
            QLineEdit {
                color: black;
                font-weight: bold;
                background-color: white;
            }
        """)
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
        self.description_edit.setStyleSheet("""
            QLineEdit {
                color: black;
                font-weight: bold;
                background-color: white;
            }
        """)
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
        self.comments_list = QListWidget()
        self.comments_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.comments_list.customContextMenuRequested.connect(self.show_comment_context_menu)
        self.layout.addWidget(self.comments_list)
        self.load_comments()

        comment_layout = QHBoxLayout()
        self.comment_edit = QLineEdit()
        self.comment_edit.setPlaceholderText("Add a new comment...")
        self.comment_edit.returnPressed.connect(self.add_comment) # Allow adding with Enter key
        self.add_comment_button = QPushButton("Add")
        self.add_comment_button.clicked.connect(self.add_comment)
        comment_layout.addWidget(self.comment_edit)
        comment_layout.addWidget(self.add_comment_button)
        self.layout.addLayout(comment_layout)

        # --- Attachments Section ---
        self.layout.addWidget(QLabel("Attachments:"))
        self.attachments_list = QListWidget()
        self.attachments_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.attachments_list.customContextMenuRequested.connect(self.show_attachment_context_menu)
        self.attachments_list.itemDoubleClicked.connect(self.open_attachment)
        self.layout.addWidget(self.attachments_list)
        self.load_attachments()

        attachment_layout = QHBoxLayout()
        self.attach_file_button = QPushButton("Attach File...")
        self.attach_file_button.clicked.connect(self.attach_file)
        attachment_layout.addStretch() # Push button to the right
        attachment_layout.addWidget(self.attach_file_button)
        self.layout.addLayout(attachment_layout)

        # --- Main Dialog Buttons ---
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def load_comments(self):
        """Loads comments into a QListWidget with custom widgets."""
        self.comments_list.clear()
        # Sort comments by timestamp for consistent order
        sorted_comments = sorted(self.task.comments, key=lambda c: c.timestamp)

        for comment in sorted_comments:
            item = QListWidgetItem(self.comments_list)
            item.setData(Qt.ItemDataRole.UserRole, comment)
            
            # --- Linkification Process ---
            url_pattern = re.compile(r'((?:https?://|www\.)[^\s<]+)')
            text_parts = url_pattern.split(comment.text)
            linked_text_parts = []
            for i, part in enumerate(text_parts):
                if i % 2 == 1:  # This part is a URL
                    url = part
                    href = url if url.startswith(('http://', 'https://')) else f'http://{url}'
                    # The displayed text is escaped, while the href is used directly.
                    linked_text_parts.append(f'<a href="{href}" style="color: #5555ff;">{html.escape(url)}</a>')
                else:  # This part is normal text, so we escape it.
                    linked_text_parts.append(html.escape(part))
            
            final_text = "".join(linked_text_parts).replace('\n', '<br>')
            # --- End Linkification ---

            author_esc = html.escape(comment.author)
            timestamp_str = comment.timestamp.strftime('%Y-%m-%d %H:%M')
            
            label = QLabel(f"<b>{author_esc}</b> <span style='color:gray;'>at {timestamp_str}:</span><br>{final_text}")
            label.setWordWrap(True)
            label.setOpenExternalLinks(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)

            item.setSizeHint(label.sizeHint())
            self.comments_list.addItem(item)
            self.comments_list.setItemWidget(item, label)
            
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

    def show_comment_context_menu(self, position):
        """Shows a context menu for editing or deleting a comment."""
        item = self.comments_list.itemAt(position)
        if not item:
            return

        comment = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(comment, Comment):
            return

        menu = QMenu()
        edit_action = menu.addAction("Edit")
        edit_action.triggered.connect(lambda: self.edit_comment(comment))
        
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(lambda: self.delete_comment(comment))
        
        menu.exec(self.comments_list.mapToGlobal(position))

    def edit_comment(self, comment: Comment):
        """Opens a dialog to edit a comment's text."""
        new_text, ok = QInputDialog.getText(self, "Edit Comment", "Comment:",
                                            QLineEdit.EchoMode.Normal, comment.text)
        if ok and new_text.strip():
            comment.text = new_text.strip()
            self.data_manager.update_task(self.task)
            self.load_comments()

    def delete_comment(self, comment: Comment):
        """Asks for confirmation and deletes a comment."""
        reply = QMessageBox.question(self, "Confirm Deletion",
                                     "Are you sure you want to delete this comment?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.task.comments.remove(comment)
            self.data_manager.update_task(self.task)
            self.load_comments()

    def load_attachments(self):
        """Loads attachments into the list widget."""
        self.attachments_list.clear()
        for rel_path in self.task.attachments:
            # Display just the filename
            filename = os.path.basename(rel_path)
            item = QListWidgetItem(filename)
            item.setData(Qt.ItemDataRole.UserRole, rel_path) # Store the relative path
            self.attachments_list.addItem(item)

    def attach_file(self):
        """Opens a file dialog to attach files to the task."""
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Select Files to Attach")
        if not file_paths:
            return

        task_attachment_dir = os.path.join(self.data_manager.attachments_dir, self.task.id)
        os.makedirs(task_attachment_dir, exist_ok=True)

        for src_path in file_paths:
            filename = os.path.basename(src_path)
            dest_path = os.path.join(task_attachment_dir, filename)

            if os.path.exists(dest_path):
                reply = QMessageBox.question(self, "File Exists",
                                             f"'{filename}' already exists. Overwrite?",
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.No:
                    continue

            try:
                shutil.copy(src_path, dest_path)
                # Store relative path from the main 'attachments' folder
                rel_path = os.path.join(self.task.id, filename)
                if rel_path not in self.task.attachments:
                    self.task.attachments.append(rel_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not attach file: {e}")

        self.data_manager.update_task(self.task)
        self.load_attachments()

    def show_attachment_context_menu(self, position):
        """Shows a context menu for opening or deleting an attachment."""
        item = self.attachments_list.itemAt(position)
        if not item: return

        menu = QMenu()
        open_action = menu.addAction("Open")
        open_action.triggered.connect(lambda: self.open_attachment(item))
        download_action = menu.addAction("Download...")
        download_action.triggered.connect(lambda: self.download_attachment(item))
        menu.addSeparator()
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(lambda: self.delete_attachment(item))
        menu.exec(self.attachments_list.mapToGlobal(position))

    def open_attachment(self, item: QListWidgetItem):
        """Opens the selected attachment with the default system application."""
        rel_path = item.data(Qt.ItemDataRole.UserRole)
        if not rel_path: return

        abs_path = os.path.join(self.data_manager.attachments_dir, rel_path)
        if os.path.exists(abs_path):
            try:
                os.startfile(abs_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open file: {e}")
        else:
            QMessageBox.warning(self, "File Not Found", "The attached file could not be found.")

    def download_attachment(self, item: QListWidgetItem):
        """Prompts the user to save a copy of the attachment to a new location."""
        rel_path = item.data(Qt.ItemDataRole.UserRole)
        if not rel_path:
            return

        src_path = os.path.join(self.data_manager.attachments_dir, rel_path)
        if not os.path.exists(src_path):
            QMessageBox.warning(self, "File Not Found", "The attached file could not be found.")
            return

        filename = os.path.basename(rel_path)
        dest_path, _ = QFileDialog.getSaveFileName(self, "Save Attachment As...", filename)

        if dest_path:
            try:
                shutil.copy(src_path, dest_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save file: {e}")

    def delete_attachment(self, item: QListWidgetItem):
        """Deletes the selected attachment."""
        rel_path = item.data(Qt.ItemDataRole.UserRole)
        if not rel_path:
            return

        filename = os.path.basename(rel_path)
        reply = QMessageBox.question(self, "Confirm Deletion",
                                     f"Are you sure you want to delete the attachment '{filename}'?\n"
                                     "This will permanently remove the file.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            # Remove the reference from the task object first
            if rel_path in self.task.attachments:
                self.task.attachments.remove(rel_path)

            # Delete the actual file from the filesystem
            abs_path = os.path.join(self.data_manager.attachments_dir, rel_path)
            if os.path.exists(abs_path):
                try:
                    os.remove(abs_path)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Could not delete file: {e}")
                    # If file deletion fails, add the reference back to be safe
                    self.task.attachments.append(rel_path)
                    return # Stop processing

            # Save the updated task and refresh the UI
            self.data_manager.update_task(self.task)
            self.load_attachments()

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
