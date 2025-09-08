import sys
from PyQt6.QtWidgets import QApplication
from app.gui.main_window import MainWindow
from app.data_manager import DataManager

def main():
    """Main application entry point."""
    app = QApplication(sys.argv)

    # Initialize data manager
    data_manager = DataManager("data/")
    data_manager.load_data() # Load existing data on startup

    # Create and show the main window
    main_window = MainWindow(data_manager)
    main_window.show()

    # Save data on exit
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

# c:\Users\xiongti\Documents\TeamTaskManager\main.py
# import sys
# from PyQt6.QtWidgets import QApplication
# from app.gui.main_window import MainWindow # Assuming your MainWindow is here
# from app.data_manager import DataManager     # Assuming your DataManager is here

# def start_app():
#     app = QApplication(sys.argv)
    
#     # Initialize your DataManager
#     # The DataManager by default creates a 'data' folder in the CWD.
#     # When the .exe runs, this 'data' folder will be created next to it.
#     data_manager = DataManager() 
    
#     main_win = MainWindow(data_manager)
#     main_win.show()
#     sys.exit(app.exec())
            
# if __name__ == '__main__':
#     start_app()
