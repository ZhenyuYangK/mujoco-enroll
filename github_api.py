"""Small GitHub REST client; credentials stay in the process environment."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class GitHubError(RuntimeError):
    def __init__(self, status, endpoint):
        self.status = status
        super().__init__(f"GitHub HTTP {status}: {endpoint}")


class GitHub:
    def __init__(self, token):
        if not token:
            raise ValueError("Missing GitHub token; configure ENROLL_GITHUB_TOKEN first.")
        self.token = token

    def api(self, method, endpoint, data=None, missing_ok=False):
        if not endpoint or endpoint.startswith(("/", "http")) or ".." in endpoint:
            raise ValueError("Invalid GitHub API endpoint")
        request = Request(
            "https://api.github.com/" + endpoint,
            data=json.dumps(data).encode() if data is not None else None,
            method=method,
            headers={"Authorization": "Bearer " + self.token,
                     "Accept": "application/vnd.github+json",
                     "Content-Type": "application/json",
                     "X-GitHub-Api-Version": "2022-11-28",
                     "User-Agent": "mujoco-learning-enrollment"},
        )
        try:
            with urlopen(request, timeout=30) as response:
                body = response.read()
                return json.loads(body) if body else None
        except HTTPError as error:
            if missing_ok and error.code == 404:
                return None
            # Response bodies can contain submitted data: never print them.
            raise GitHubError(error.code, endpoint) from None
        except (URLError, TimeoutError, OSError):
            raise RuntimeError("GitHub request failed; retry this application later.") from None


def redact(message):
    for key in ("GH_TOKEN", "ENROLL_GITHUB_TOKEN", "ISSUE_TOKEN"):
        token = os.environ.get(key)
        if token:
            message = message.replace(token, "[REDACTED]")
    return message
