import unittest
import uuid
from datetime import datetime
from app.data_models import TeamMember, Task, TaskStatus, Comment

class TestDataModels(unittest.TestCase):

    def test_create_team_member(self):
        member_name = "Alice Wonderland"
        member = TeamMember(name=member_name)
        self.assertIsInstance(member.id, str)
        try:
            uuid.UUID(member.id, version=4) # Check if it's a valid UUID v4
        except ValueError:
            self.fail("TeamMember ID is not a valid UUID v4")
        self.assertEqual(member.name, member_name)

    def test_create_task_defaults(self):
        task_description = "Review project proposal"
        member_id = str(uuid.uuid4())
        task = Task(description=task_description, assigned_to=member_id)

        self.assertIsInstance(task.id, str)
        self.assertEqual(task.description, task_description)
        self.assertEqual(task.status, TaskStatus.PENDING)
        self.assertEqual(len(task.comments), 0)
        self.assertIsInstance(task.created_at, datetime)
        self.assertEqual(task.assigned_to, member_id)

    def test_create_task_with_specific_status(self):
        task = Task(description="Follow up", status=TaskStatus.DONE)
        self.assertEqual(task.status, TaskStatus.DONE)

    def test_create_comment(self):
        comment_text = "This looks good."
        author_name = "Bob The Builder"
        comment = Comment(text=comment_text, author=author_name)

        self.assertEqual(comment.text, comment_text)
        self.assertEqual(comment.author, author_name)
        self.assertIsInstance(comment.timestamp, datetime)

    def test_comment_to_dict_and_from_dict(self):
        original_text = "Needs more detail on section 3."
        original_author = "Carol Danvers"
        original_timestamp = datetime.now() # Use a fixed time for more precise comparison if needed

        comment = Comment(text=original_text, author=original_author, timestamp=original_timestamp)
        comment_dict = comment.to_dict()

        self.assertEqual(comment_dict["text"], original_text)
        self.assertEqual(comment_dict["author"], original_author)
        self.assertEqual(comment_dict["timestamp"], original_timestamp.isoformat())

        rehydrated_comment = Comment.from_dict(comment_dict)
        self.assertEqual(rehydrated_comment.text, original_text)
        self.assertEqual(rehydrated_comment.author, original_author)
        # Timestamps might have microsecond differences after isoformat conversion and back
        self.assertAlmostEqual(rehydrated_comment.timestamp, original_timestamp, delta=datetime.min.resolution)

if __name__ == '__main__':
    unittest.main()