# c:\Users\xiongti\Documents\TeamTaskManager\app\gui\main_window.py
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QMenuBar, QMessageBox,
                             QStatusBar, QHBoxLayout, QMenu, QInputDialog, QLineEdit, QSplitter, QListWidget,
                             QListWidgetItem, QPushButton)
from PyQt6.QtGui import QAction, QKeySequence, QColor, QPixmap, QPalette, QBrush, QPainter, QFont
from PyQt6.QtCore import Qt, QTimer, QDateTime, QRect, QDate
from ..data_manager import DataManager # Import DataManager
from .dialogs import AddTaskListDialog
from .daily_todo_widget import DailyTodoWidget
from .overview_window import OverviewWindow
from ..data_models import TaskStatus, TaskList
# Attempt to import plyer for native notifications
try:
    from plyer import notification
except ImportError:
    notification = None # Fallback if plyer is not installed

import os # For path joining
from typing import Optional

class TaskWorkspaceWidget(QWidget):
    """A widget that contains the list panel on the left and the task view on the right."""
    def __init__(self, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.current_context_id: Optional[str] = None
        self.current_context_category: str = 'default'

        # --- Layout ---
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- Left Panel for Lists ---
        self.list_panel = QWidget()
        panel_layout = QVBoxLayout(self.list_panel)
        panel_layout.setContentsMargins(5, 5, 5, 5)
        
        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self.on_list_selected)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_list_context_menu)
        
        self.add_list_button = QPushButton("Add List")
        self.add_list_button.clicked.connect(self.add_list)

        self.lists_label = QLabel("Lists:")
        self.lists_label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.lists_label.customContextMenuRequested.connect(self.show_add_list_menu_on_label)

        panel_layout.addWidget(self.lists_label)
        panel_layout.addWidget(self.list_widget)
        panel_layout.addWidget(self.add_list_button)
        
        # --- Central Task View ---
        self.daily_todo_widget = DailyTodoWidget(self.data_manager)

        splitter.addWidget(self.list_panel)
        splitter.addWidget(self.daily_todo_widget)
        splitter.setSizes([200, 800]) # Initial sizes

        self.main_layout.addWidget(splitter)

        self.list_panel.setVisible(False) # Initially hidden

    def load_context(self, context_id: Optional[str]):
        self.current_context_id = context_id
        self.list_panel.setVisible(True)

        if context_id == "__DEFAULT_LISTS__":
            self.current_context_category = 'default'
        else: # It's a project block ID
            self.current_context_category = f"project_{context_id}"
        
        self.refresh_list_panel()

    def refresh_list_panel(self):
        self.list_widget.clear()
        
        all_lists = self.data_manager.get_all_task_lists()
        lists_for_context = [
            tl for tl in all_lists if getattr(tl, 'category', 'default') == self.current_context_category
        ]

        sorted_lists = sorted(lists_for_context, key=lambda tl: tl.name)

        for task_list in sorted_lists:
            item = QListWidgetItem(task_list.name)
            item.setData(Qt.ItemDataRole.UserRole, task_list)
            self.list_widget.addItem(item)
        
        if sorted_lists:
            # If there are lists, automatically select the first one.
            first_item = self.list_widget.item(0)
            if first_item:
                self.list_widget.setCurrentItem(first_item)
                self.on_list_selected(first_item)
        else:
            # If there are no lists, show a more helpful placeholder.
            self.daily_todo_widget.show_placeholder_message("This workspace is empty. Add a list to get started.")
    
    def on_list_selected(self, item: QListWidgetItem):
        task_list = item.data(Qt.ItemDataRole.UserRole)
        if task_list:
            self.daily_todo_widget.set_task_list_and_date(task_list, self.daily_todo_widget.current_date.toPyDate())

    def add_list(self):
        dialog = AddTaskListDialog(self)
        if dialog.exec():
            name = dialog.get_name()
            task_list = self.data_manager.add_task_list(name, category=self.current_context_category)
            if task_list:
                self.refresh_list_panel()
                # Automatically select the new list
                items = self.list_widget.findItems(task_list.name, Qt.MatchFlag.MatchExactly)
                if items:
                    self.list_widget.setCurrentItem(items[0])
                    self.on_list_selected(items[0])
            else:
                QMessageBox.warning(self, "Failed", f"Could not add Task List '{name}'. It might already exist.")

    def show_list_context_menu(self, position):
        item = self.list_widget.itemAt(position)
        menu = QMenu()

        if item:
            task_list = item.data(Qt.ItemDataRole.UserRole)
            if not task_list: return

            rename_action = menu.addAction("Rename")
            rename_action.triggered.connect(lambda: self.rename_list(task_list))
            delete_action = menu.addAction("Delete")
            delete_action.triggered.connect(lambda: self.delete_list(task_list))
        else:
            # Show 'Add List' when clicking on empty space
            add_action = menu.addAction("Add List...")
            add_action.triggered.connect(self.add_list)

        if not menu.isEmpty():
            menu.exec(self.list_widget.mapToGlobal(position))

    def show_add_list_menu_on_label(self, position):
        """Shows a context menu on the 'Lists' label to add a new list."""
        menu = QMenu()
        add_action = menu.addAction("Add List...")
        add_action.triggered.connect(self.add_list)
        menu.exec(self.lists_label.mapToGlobal(position))

    def rename_list(self, task_list: TaskList):
        # This method will be called by MainWindow to refresh the Team menu
        self.parent().rename_task_list(task_list.id)
        self.refresh_list_panel()

    def delete_list(self, task_list: TaskList):
        # This method will be called by MainWindow to refresh the Team menu
        self.parent().delete_task_list(task_list.id)
        self.refresh_list_panel()

class MainWindow(QMainWindow):
    _triggered_alarms: set[str] = set() # Class variable to track triggered alarms
    def __init__(self, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.setWindowTitle("MyTasks") # You can change this to your desired title
        self.setGeometry(100, 100, 1000, 700) # x, y, width, height

        # self.top_image_banner_height = 60  # No longer needed
        # self.original_bg_pixmap: QPixmap | None = None # No longer needed

        self._create_actions()
        self._create_menu_bar()
        self._create_status_bar()

        self.overview_window = None
        self._create_central_widget()
        self._load_last_view()

        self.update_time_display()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time_display)
        self.timer.start(1000) # Update clock every second
        
        # self._load_original_background_image() # No longer needed
        self.setAutoFillBackground(True)       # Crucial for QMainWindow to draw its background

        # Alarm Timer
        self.alarm_timer = QTimer(self)
        self.alarm_timer.timeout.connect(self.check_for_alarms)
        self.alarm_timer.start(5 * 60 * 1000) # Check for alarms every 5 minutes


        # Set QMainWindow's own background to light green
        main_window_palette = self.palette()
        main_window_palette.setColor(QPalette.ColorRole.Window, QColor(144, 238, 144)) # Light green
        self.setPalette(main_window_palette)

    def _create_actions(self):

        self.show_overview_action = QAction("&Show Overview", self)
        self.show_overview_action.triggered.connect(self.show_overview)

        self.exit_action = QAction("E&xit", self)
        self.exit_action.triggered.connect(self.close) # QMainWindow's close
        self.exit_action.setShortcut(QKeySequence.StandardKey.Quit)

    def _create_menu_bar(self):
        menu_bar = self.menuBar()

        # --- Make menubar's background transparent and style items ---
        menu_bar.setAutoFillBackground(False) # Tell the menubar NOT to draw its own palette background
        # No direct palette manipulation for transparency here; we'll rely on the stylesheet.
        menu_bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True) # Crucial for stylesheet to control background



        menu_bar.setStyleSheet("""
            QMenuBar {
                background: transparent; /* Explicitly make the menubar background transparent */
                border: none; /* Remove any default border that might be opaque */
            }
            QMenuBar::item {
                color: black; /* Text color for items like "File", "Team" */
                background: transparent; /* Ensure item background is also transparent */
                padding: 4px 8px; /* Add some padding for better visual separation */
                margin: 2px; /* Add small margin around items */
            }
            QMenuBar::item:selected { /* When item is hovered or menu is open */
                background: rgba(0, 0, 0, 30); /* Subtle dark semi-transparent highlight */
                border-radius: 4px;
            }
            QMenuBar::item:pressed { /* When item is clicked */
                background: rgba(0, 0, 0, 50); /* Slightly darker highlight on press */
                border-radius: 4px;
            }
        """)
        
        # File Menu
        file_menu = menu_bar.addMenu("&File")

        file_menu.addAction(self.show_overview_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        # Workspace Menu (will be populated dynamically)
        self.workspace_menu = menu_bar.addMenu("&Workspace")
        self.refresh_workspace_menu()

    def _create_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.time_label = QLabel()
        self.status_bar.addPermanentWidget(self.time_label)

    def _create_central_widget(self):
        # The central widget will now be the DailyTodoWidget, initially hidden or showing a placeholder
        self.workspace = TaskWorkspaceWidget(self.data_manager, self)
        self.setCentralWidget(self.workspace)

        # Set background for the central widget (DailyTodoWidget)
        self.workspace.setAutoFillBackground(True)
        light_green_palette = self.workspace.palette()
        light_green_palette.setColor(QPalette.ColorRole.Window, QColor(144, 238, 144)) # Light green
        self.workspace.setPalette(light_green_palette)

    def _load_last_view(self):
        """Loads the last viewed task list/block from settings."""
        last_context_id = self.data_manager.load_setting('last_selected_context_id')
        if last_context_id:
            # Check if the context still exists before loading
            if last_context_id == "__DEFAULT_LISTS__" or self.data_manager.get_task_list_by_id(last_context_id):
                 self.workspace.load_context(last_context_id)

    def switch_to_all_task_lists(self, save_setting: bool = True):
        """Switches to the combined view of all 'default' task lists."""
        context_id = "__DEFAULT_LISTS__"
        self.workspace.load_context(context_id)
        if save_setting:
            self.data_manager.save_setting('last_selected_context_id', context_id)

    def switch_to_task_list(self, list_id: str, save_setting: bool = True):
        """Switches the main view to show the selected task list."""
        # This is now switching to a 'block' context
        self.workspace.load_context(list_id)
        if save_setting:
            self.data_manager.save_setting('last_selected_context_id', list_id)

    def rename_task_list(self, list_id: str):
        """Handles the logic for renaming a task list."""
        task_list = self.data_manager.get_task_list_by_id(list_id)
        if not task_list:
            QMessageBox.warning(self, "Error", "Task List not found.")
            return

        is_block = getattr(task_list, 'category', 'default') == 'project'
        title = "Rename Workspace" if is_block else "Rename Task List"

        new_name, ok = QInputDialog.getText(self, title,
                                            "Enter new name for it:",
                                            QLineEdit.EchoMode.Normal,
                                            task_list.name)

        if ok and new_name.strip() and new_name.strip() != task_list.name:
            stripped_name = new_name.strip()
            if self.data_manager.update_task_list_name(list_id, stripped_name):
                self.refresh_workspace_menu()
                # The workspace will refresh its own list panel.
                # We just need to handle if the active block itself was renamed.
                if self.workspace.current_context_id == list_id:
                    # Reload context to update titles etc. if needed (future enhancement)
                    pass
            else:
                QMessageBox.warning(self, "Error", f"Could not rename Task List. A list with the name '{stripped_name}' might already exist.")

    def delete_task_list(self, list_id: str):
        task_list = self.data_manager.get_task_list_by_id(list_id)
        if not task_list:
            QMessageBox.warning(self, "Error", "Task List not found.")
            return

        is_block = getattr(task_list, 'category', 'default') == 'project'
        item_type = "Workspace" if is_block else "Task List"

        reply = QMessageBox.question(self, "Confirm Deletion",
                                     f"Are you sure you want to delete {item_type} '{task_list.name}'?\n"
                                     "Tasks associated with it will be unassigned.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            if self.data_manager.delete_task_list(list_id):
                QMessageBox.information(self, "Success", f"{item_type} '{task_list.name}' deleted.")
                self.refresh_workspace_menu()
                # If the deleted item was the active context, clear the workspace
                if self.workspace.current_context_id == list_id:
                    self.data_manager.save_setting('last_selected_context_id', None)
                    self.workspace.list_panel.setVisible(False)
                    # Reset the view to the initial placeholder message
                    self.workspace.daily_todo_widget.show_placeholder_message("Select a workspace from the 'Team' menu to begin.")

            else:
                QMessageBox.warning(self, "Error", f"Could not delete Task List '{task_list.name}'.")

    def update_time_display(self):
        now = QDateTime.currentDateTime()
        week_number = now.date().weekNumber()[0]
        self.time_label.setText(f"{now.toString('dddd, MMMM d, yyyy hh:mm:ss ap')} (Week {week_number})")

    def show_overview(self):
        if not self.overview_window or not self.overview_window.isVisible():
            self.overview_window = OverviewWindow(self.data_manager, self) # Create if doesn't exist
        self.overview_window.show()
        self.overview_window.raise_() # Bring to front
        self.overview_window.activateWindow()

    # --- New methods for Task Blocks ---

    def refresh_workspace_menu(self):
        self.workspace_menu.clear()

        add_workspace_action = self.workspace_menu.addAction("Add Workspace...")
        add_workspace_action.triggered.connect(self.add_workspace)

        self.workspace_menu.addSeparator()

        # --- Get and sort lists into categories ---
        default_lists = []
        project_lists = []
        for tl in self.data_manager.get_all_task_lists():
            if getattr(tl, 'category', 'default') == 'project':
                project_lists.append(tl)
            else:
                default_lists.append(tl)

        # --- Add the static "TaskLists" block ---
        # This is a single entry that represents all default lists combined.
        tasklists_menu = self.workspace_menu.addMenu("📋 TaskLists")
        switch_all_action = tasklists_menu.addAction("Open Workspace")
        switch_all_action.triggered.connect(self.switch_to_all_task_lists)

        # --- Add individual "Task Blocks" ---
        for task_block in sorted(project_lists, key=lambda p: p.name):
            item_menu_title = f"📦 {task_block.name}"
            
            item_menu = self.workspace_menu.addMenu(item_menu_title)
            switch_action = item_menu.addAction("Open Workspace")
            switch_action.triggered.connect(lambda checked=False, l_id=task_block.id: self.switch_to_task_list(l_id))
            item_menu.addSeparator()
            rename_action = item_menu.addAction("Rename")
            rename_action.triggered.connect(lambda checked=False, l_id=task_block.id: self.rename_task_list(l_id))
            delete_action = item_menu.addAction("Delete")
            delete_action.triggered.connect(lambda checked=False, l_id=task_block.id: self.delete_task_list(l_id))

        # --- Handle case where there's nothing but the "TaskLists" entry ---
        if not default_lists and not project_lists:
            self.workspace_menu.addSeparator()
            no_items_action = self.workspace_menu.addAction("No lists or blocks yet")
            no_items_action.setEnabled(False)

    def add_workspace(self):
        name, ok = QInputDialog.getText(self, "Add Workspace", "Enter name for the new Workspace:")
        if ok and name.strip():
            # Add a task list with the 'project' category
            task_list = self.data_manager.add_task_list(name.strip(), category='project')
            if task_list:
                QMessageBox.information(self, "Success", f"Workspace '{task_list.name}' added.")
                self.refresh_workspace_menu()
            else:
                QMessageBox.warning(self, "Failed", f"Could not add Workspace '{name}'. It might already exist.")

    def check_for_alarms(self):
        """Checks tasks for upcoming due times and triggers alarms."""
        print(f"\n[{QDateTime.currentDateTime().toString('yyyy-MM-dd HH:mm:ss')}] Running check_for_alarms...")
        now = QDateTime.currentDateTime().toPyDateTime()
        # Check tasks that are not done and have a due time
        tasks_to_check = [
            task for task in self.data_manager.tasks.values()
            if task.status != TaskStatus.DONE and task.due_at is not None and task.id not in self._triggered_alarms
        ]
        print(f"Found {len(tasks_to_check)} tasks eligible for alarm check (not DONE, has due_at, alarm not yet triggered this session).")

        for task in tasks_to_check:
            print(f"  Checking task: '{task.description}' (ID: {task.id})")
            print(f"    Status: {task.status.value}, Due at: {task.due_at}, Now: {now}")
            time_until_due = task.due_at - now
            seconds_until_due = time_until_due.total_seconds()
            print(f"    Time until due: {time_until_due} (Seconds: {seconds_until_due})")
            
            # Trigger alarm if due within the next 12 hours (and not already due)
            # Use a small epsilon to handle floating point comparisons near zero
            if seconds_until_due > 0 and seconds_until_due <= 12 * 3600: # 12 hours = 43200 seconds
                print(f"    ALARM TRIGGERING for task: {task.description}")
                task_list = self.data_manager.get_task_list_by_id(task.assigned_to)
                member_name = task_list.name if task_list else "an unassigned list"
                
                notification_title = "Team Task Due Soon!"
                notification_message = f"Task '{task.description}' assigned to {member_name} is due within 12 hours ({task.due_at.strftime('%Y-%m-%d %H:%M')})."

                if notification: # Use plyer for native notifications if available
                    try:
                        notification.notify(
                            title=notification_title,
                            message=notification_message,
                            app_name='Team Task Manager',
                            timeout=10  # Notification will disappear after 10 seconds
                        )
                        print("    --> Sent native notification via plyer.")
                    except Exception as e:
                        print(f"    --> Plyer notification failed: {e}. Falling back to QMessageBox.")
                        self._show_qmessagebox_alarm(notification_title, notification_message)
                else: # Fallback to QMessageBox
                    print("    --> Plyer not available. Using QMessageBox for alarm.")
                    self._show_qmessagebox_alarm(notification_title, notification_message)

                self._triggered_alarms.add(task.id) # Mark alarm as triggered for this session
            else:
                print(f"    No alarm for task: {task.description}. (Condition: {seconds_until_due > 0} and {seconds_until_due <= 12 * 3600})")

    def _show_qmessagebox_alarm(self, title: str, message: str):
        """Displays a modal QMessageBox alarm as a fallback."""
        alarm_dialog = QMessageBox(self)
        alarm_dialog.setIcon(QMessageBox.Icon.Warning)
        alarm_dialog.setWindowTitle(title)
        alarm_dialog.setText(message)
        alarm_dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        
        QApplication.alert(alarm_dialog, 0) # Request OS to alert user (e.g., flash taskbar)
        alarm_dialog.exec()

    def closeEvent(self, event):
        # Override closeEvent to save data before exiting
        # No need for a dialog here if we always save on close,
        # but good practice if there are unsaved changes that aren't auto-saved.
        print("Saving data on exit...")
        self.data_manager.save_data()
        super().closeEvent(event) # Call the base class closeEvent

    # def _load_original_background_image(self): # No longer needed
        # """Loads the background image from file into self.original_bg_pixmap."""
        # ... (implementation removed)

    # def paintEvent(self, event): # No longer needed for custom banner
        # ... (implementation removed)

    def resizeEvent(self, event):
        super().resizeEvent(event) # Important to call the base class's implementation
        # self.update() # No longer needed as custom paintEvent is removed
