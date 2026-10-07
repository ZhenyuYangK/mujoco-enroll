import copy
import json
from pathlib import Path
import unittest

from enroll import parse_request, provision, validate_config

CONFIG = json.loads((Path(__file__).resolve().parents[1] / "course.json").read_text())


class FakeGitHub:
    def __init__(self):
        self.repo = None
        self.variable = None
        self.calls = []

    def api(self, method, endpoint, data=None, missing_ok=False):
        self.calls.append((method, endpoint, data))
        if endpoint.endswith("/generate"):
            self.repo = {"full_name": CONFIG["owner"] + "/" + data["name"],
                         "description": data["description"], "private": data["private"],
                         "template_repository": {"full_name": CONFIG["owner"] + "/" + CONFIG["template_repo"]}}
            return self.repo
        if endpoint == "repos/" + CONFIG["owner"] + "/" + CONFIG["template_repo"]:
            return {"is_template": True, "default_branch": "main"}
        if endpoint.endswith("/branches/main"):
            return {"name": "main"}
        if endpoint.endswith("/actions/variables/STUDENT_GITHUB"):
            return self.variable
        if endpoint.endswith("/actions/variables"):
            self.variable = copy.deepcopy(data)
            return self.variable
        if method == "GET":
            return self.repo
        return None


class EnrollmentTests(unittest.TestCase):
    def test_config(self):
        validate_config(CONFIG)
        for field, value in [("owner", "bad/owner"), ("repo_prefix", "../x"), ("enrollment_open", False)]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_config({**CONFIG, field: value})

    def test_author_is_identity(self):
        issue = {"user": {"login": "alice", "type": "User"},
                 "body": "### 课程\n\n" + CONFIG["title"] + "\n\n### GitHub\n\nadmin"}
        self.assertEqual(parse_request(issue, CONFIG), "alice")
        for change in [{"pull_request": {}}, {"user": {"login": "bot", "type": "Bot"}},
                       {"body": "### 课程\n\nUnknown"}, {"body": issue["body"] + "\n### 课程\n\nOther"}]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                parse_request({**issue, **change}, CONFIG)

    def test_legacy_course_title_can_be_retried(self):
        issue = {"user": {"login": "alice", "type": "User"},
                 "body": "### 课程\n\nMuJoCo 基础与机器人仿真"}
        self.assertEqual(parse_request(issue, CONFIG), "alice")

    def test_repeat_does_not_regenerate(self):
        client = FakeGitHub()
        first = provision(client, CONFIG, "alice", sleep=lambda _: None)
        second = provision(client, CONFIG, "alice", sleep=lambda _: None)
        self.assertEqual(first, second)
        self.assertEqual(sum(path.endswith("/generate") for _, path, _ in client.calls), 1)
        self.assertEqual(client.variable["value"], "alice")
        self.assertTrue(any(path.endswith("/collaborators/alice") for _, path, _ in client.calls))
        self.assertTrue(any(path.endswith("grade.yml/dispatches") for _, path, _ in client.calls))

    def test_foreign_repository_is_untouched(self):
        client = FakeGitHub()
        client.repo = {"template_repository": {"full_name": "someone/other"}, "private": False}
        with self.assertRaises(ValueError):
            provision(client, CONFIG, "alice", sleep=lambda _: None)
        self.assertFalse(any(method != "GET" for method, _, _ in client.calls))

    def test_foreign_student_is_untouched(self):
        client = FakeGitHub()
        provision(client, CONFIG, "alice", sleep=lambda _: None)
        client.variable["value"] = "bob"
        client.calls.clear()
        with self.assertRaises(ValueError):
            provision(client, CONFIG, "alice", sleep=lambda _: None)
        self.assertFalse(any(method != "GET" for method, _, _ in client.calls))

    def test_owner_does_not_invite_self(self):
        client = FakeGitHub()
        provision(client, CONFIG, CONFIG["owner"], sleep=lambda _: None)
        self.assertFalse(any("/collaborators/" in path for _, path, _ in client.calls))


if __name__ == "__main__":
    unittest.main()
