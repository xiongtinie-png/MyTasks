# c:\Users\xiongti\Documents\TeamTaskManager\app\gui\main_window.py
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QMenuBar, QMessageBox,
                             QStatusBar, QDockWidget, QListWidget, QListWidgetItem, QHBoxLayout, QMenu, QInputDialog, QLineEdit)
from PyQt6.QtGui import QAction, QKeySequence, QColor, QPixmap, QPalette, QBrush, QPainter
from PyQt6.QtCore import Qt, QTimer, QDateTime, QRect
from ..data_manager import DataManager # Import DataManager
from .dialogs import AddTaskListDialog, TaskDetailsDialog # AddTaskDialog is used in DailyTodoWidget
from .daily_todo_widget import DailyTodoWidget
from .overview_window import OverviewWindow
from ..data_models import TaskStatus

# Attempt to import plyer for native notifications
try:
    from plyer import notification
except ImportError:
    notification = None # Fallback if plyer is not installed

import os # For path joining
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

        # Initialize widgets that might be used by other setup methods
        # It's crucial to initialize self.daily_todo_widget before methods that use it, like _create_central_widget.
        self.daily_todo_widget = DailyTodoWidget(self.data_manager)
        self.overview_window = None

        self._create_task_lists_panel() # Create panel before central widget
        self._create_central_widget()

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
        self.add_task_list_action = QAction("&Add Task List...", self)
        self.add_task_list_action.triggered.connect(self.add_task_list)
        self.add_task_list_action.setShortcut(QKeySequence.StandardKey.New)

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

        file_menu.addAction(self.add_task_list_action)
        file_menu.addSeparator()
        file_menu.addAction(self.show_overview_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        # Team Menu (will be populated dynamically or have a sub-widget)
        self.team_menu = menu_bar.addMenu("&Team")
        # We'll populate this later or use a dedicated panel

    def _create_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.time_label = QLabel()
        self.status_bar.addPermanentWidget(self.time_label)

    def _create_central_widget(self):
        # The central widget will now be the DailyTodoWidget, initially hidden or showing a placeholder
        self.setCentralWidget(self.daily_todo_widget)

        # Set background for the central widget (DailyTodoWidget)
        self.daily_todo_widget.setAutoFillBackground(True)
        light_green_palette = self.daily_todo_widget.palette()
        light_green_palette.setColor(QPalette.ColorRole.Window, QColor(144, 238, 144)) # Light green
        self.daily_todo_widget.setPalette(light_green_palette)
        self.daily_todo_widget.setVisible(False) # Initially hidden until a member is selected

    def _create_task_lists_panel(self):
        self.task_lists_dock = QDockWidget("Task Lists", self)
        self.task_lists_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)

        self.task_list_widget = QListWidget()
        self.task_list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.task_list_widget.customContextMenuRequested.connect(self.show_task_list_context_menu)
        self.task_list_widget.itemClicked.connect(self.on_task_list_selected)
        self.task_lists_dock.setWidget(self.task_list_widget)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.task_lists_dock)
        self.refresh_task_lists_panel()

    def refresh_task_lists_panel(self):
        self.task_list_widget.clear()
        task_lists = self.data_manager.get_all_task_lists()
        for task_list in sorted(task_lists, key=lambda tl: tl.name):
            item = QListWidgetItem(task_list.name)
            item.setData(Qt.ItemDataRole.UserRole, task_list.id) # Store list ID with the item
            self.task_list_widget.addItem(item)

    def on_task_list_selected(self, item: QListWidgetItem):
        list_id = item.data(Qt.ItemDataRole.UserRole)
        task_list = self.data_manager.get_task_list_by_id(list_id)
        if task_list:
            self.daily_todo_widget.set_task_list_and_date(task_list, self.daily_todo_widget.current_date.toPyDate())
            self.daily_todo_widget.setVisible(True)

    def show_task_list_context_menu(self, position):
        selected_item = self.task_list_widget.itemAt(position)
        if not selected_item:
            return

        list_id = selected_item.data(Qt.ItemDataRole.UserRole)
        task_list = self.data_manager.get_task_list_by_id(list_id)
        if not task_list:
            return

        menu = QMenu()
        rename_action = menu.addAction("Rename Task List")
        rename_action.triggered.connect(lambda: self.rename_task_list(list_id))
        menu.addSeparator()
        delete_action = menu.addAction("Delete Task List")
        delete_action.triggered.connect(lambda: self.delete_task_list(list_id))
        menu.exec(self.task_list_widget.mapToGlobal(position))

    def rename_task_list(self, list_id: str):
        """Handles the logic for renaming a task list."""
        task_list = self.data_manager.get_task_list_by_id(list_id)
        if not task_list:
            QMessageBox.warning(self, "Error", "Task List not found.")
            return

        new_name, ok = QInputDialog.getText(self, "Rename Task List",
                                            "Enter new name:",
                                            QLineEdit.EchoMode.Normal,
                                            task_list.name)

        if ok and new_name.strip() and new_name.strip() != task_list.name:
            stripped_name = new_name.strip()
            if self.data_manager.update_task_list_name(list_id, stripped_name):
                self.refresh_task_lists_panel()
                # If the renamed list is currently active, update its title in the main view
                if self.daily_todo_widget.isVisible() and self.daily_todo_widget.current_task_list and self.daily_todo_widget.current_task_list.id == list_id:
                    refreshed_task_list = self.data_manager.get_task_list_by_id(list_id)
                    self.daily_todo_widget.set_task_list_and_date(refreshed_task_list, self.daily_todo_widget.current_date.toPyDate())
            else:
                QMessageBox.warning(self, "Error", f"Could not rename Task List. A list with the name '{stripped_name}' might already exist.")

    def delete_task_list(self, list_id: str):
        task_list = self.data_manager.get_task_list_by_id(list_id)
        if not task_list:
            QMessageBox.warning(self, "Error", "Task List not found.")
            return

        reply = QMessageBox.question(self, "Confirm Deletion",
                                     f"Are you sure you want to delete Task List '{task_list.name}'?\n"
                                     "Tasks assigned to this list will be unassigned.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            if self.data_manager.delete_task_list(list_id):
                QMessageBox.information(self, "Success", f"Task List '{task_list.name}' deleted.")
                self.refresh_task_lists_panel()
                # If the deleted member was the one whose tasks are currently shown, hide the daily_todo_widget
                if self.daily_todo_widget.isVisible() and self.daily_todo_widget.current_task_list and self.daily_todo_widget.current_task_list.id == list_id:
                    self.daily_todo_widget.setVisible(False)
            else:
                QMessageBox.warning(self, "Error", f"Could not delete Task List '{task_list.name}'.")

    def update_time_display(self):
        now = QDateTime.currentDateTime()
        week_number = now.date().weekNumber()[0]
        self.time_label.setText(f"{now.toString('dddd, MMMM d, yyyy hh:mm:ss ap')} (Week {week_number})")

    def add_task_list(self):
        dialog = AddTaskListDialog(self)
        if dialog.exec(): # exec() returns 1 (Accepted) or 0 (Rejected)
            name = dialog.get_name()
            task_list = self.data_manager.add_task_list(name)
            if task_list:
                QMessageBox.information(self, "Success", f"Task List '{task_list.name}' added.")
                self.refresh_task_lists_panel()
            else:
                QMessageBox.warning(self, "Failed", f"Could not add Task List '{name}'. It might already exist.")

    def show_overview(self):
        if not self.overview_window or not self.overview_window.isVisible():
            self.overview_window = OverviewWindow(self.data_manager, self) # Create if doesn't exist
        self.overview_window.show()
        self.overview_window.raise_() # Bring to front
        self.overview_window.activateWindow()

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
