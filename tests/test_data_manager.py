import unittest
import os
import shutil
import tempfile
from datetime import date

from app.data_manager import DataManager
from app.data_models import TaskStatus, TeamMember

class TestDataManager(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory for test data
        self.test_dir = tempfile.mkdtemp()
        self.data_manager = DataManager(data_folder_path=self.test_dir)
        # print(f"Test data will be stored in: {self.test_dir}")

    def tearDown(self):
        # Remove the temporary directory after the test
        shutil.rmtree(self.test_dir)
        # print(f"Cleaned up test data directory: {self.test_dir}")

    def test_add_and_get_team_member(self):
        member_name = "Test User One"
        added_member = self.data_manager.add_team_member(member_name)
        self.assertIsNotNone(added_member)
        self.assertEqual(added_member.name, member_name)

        retrieved_member = self.data_manager.get_team_member_by_id(added_member.id)
        self.assertIsNotNone(retrieved_member)
        self.assertEqual(retrieved_member.name, member_name)

        all_members = self.data_manager.get_all_team_members()
        self.assertEqual(len(all_members), 1)
        self.assertEqual(all_members[0].name, member_name)

    def test_add_duplicate_team_member(self):
        member_name = "Test User Two"
        self.data_manager.add_team_member(member_name) # Add first time
        duplicate_member = self.data_manager.add_team_member(member_name) # Add second time
        self.assertIsNone(duplicate_member, "Adding a duplicate member should return None")

    def test_add_task_for_member(self):
        member = self.data_manager.add_team_member("Task Assignee")
        self.assertIsNotNone(member)

        task_desc = "Do important work"
        task = self.data_manager.add_task(description=task_desc, assigned_to_id=member.id)
        self.assertIsNotNone(task)
        self.assertEqual(task.description, task_desc)
        self.assertEqual(task.assigned_to, member.id)
        self.assertEqual(task.status, TaskStatus.PENDING)

if __name__ == '__main__':
    unittest.main()