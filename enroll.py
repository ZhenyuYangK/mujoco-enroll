"""Create an individual MuJoCo repository for the issue author."""

import json
import os
from pathlib import Path
import re
import sys
import time

from github_api import GitHub, GitHubError, redact

ROOT = Path(__file__).resolve().parent
LOGIN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?")
REPO = re.compile(r"[A-Za-z0-9_.-]{1,100}")


def validate_config(config):
    if not LOGIN.fullmatch(config.get("owner", "")):
        raise ValueError("Configure a valid owner in course.json")
    for field in ("enroll_repo", "template_repo", "repo_prefix"):
        if not REPO.fullmatch(config.get(field, "")) or config[field] in (".", ".."):
            raise ValueError("Invalid course repository name: " + field)
    if type(config.get("private")) is not bool or config.get("enrollment_open") is not True:
        raise ValueError("Enrollment is closed or course configuration is invalid.")
    if len(config["repo_prefix"]) > 60:
        raise ValueError("Repository prefix is too long")


def parse_request(issue, config):
    if issue.get("pull_request") is not None:
        raise ValueError("Pull requests are not enrollment requests")
    user = issue.get("user", {})
    login = user.get("login", "")
    if user.get("type") != "User" or not LOGIN.fullmatch(login):
        raise ValueError("A personal GitHub account must submit the request")
    courses = re.findall(r"^### 课程\s*\n+([^\n]+)", issue.get("body") or "", re.MULTILINE)
    titles = [config["title"], *config.get("legacy_titles", [])]
    if len(courses) != 1 or courses[0] not in titles:
        raise ValueError("请使用 MuJoCo 领取申请表；课程字段必须与课程配置一致。")
    return login


def validate_existing(repo, template, marker, private):
    source = (repo.get("template_repository") or {}).get("full_name", "")
    if (source.lower() != template.lower() or repo.get("description") != marker
            or repo.get("private") != private or repo.get("archived") or repo.get("disabled")):
        raise ValueError("Repository name already exists with a different identity; nothing was overwritten.")


def provision(client, config, login, sleep=time.sleep):
    owner = config["owner"]
    template = owner + "/" + config["template_repo"]
    repository = owner + "/" + config["repo_prefix"] + "-" + login
    marker = "mujoco-learning:v1 student=" + login.lower()
    source = client.api("GET", "repos/" + template)
    if (not source.get("is_template") or source.get("archived") or source.get("disabled")
            or source.get("default_branch") != "main"):
        raise ValueError("Course source must be an active template repository with main as its default branch")
    client.api("GET", "repos/" + template + "/branches/main")
    endpoint = "repos/" + repository
    repo = client.api("GET", endpoint, missing_ok=True)
    if repo is None:
        try:
            repo = client.api("POST", "repos/" + template + "/generate", {
                "owner": owner, "name": repository.split("/")[1],
                "description": marker, "private": config["private"],
                "include_all_branches": False,
            })
        except (GitHubError, RuntimeError) as error:
            if isinstance(error, GitHubError) and error.status not in (422, 500, 502, 503, 504):
                raise
            # Creation may have succeeded despite a lost response; reconcile identity.
            repo = client.api("GET", endpoint, missing_ok=True)
            if repo is None:
                raise error
        # Template generation can return before template_repository is populated.
        # Read the canonical repository before checking its identity or granting access.
        for attempt in range(30):
            repo = client.api("GET", endpoint, missing_ok=True)
            if repo and repo.get("template_repository"):
                break
            sleep(2)
        else:
            raise RuntimeError("Template identity is still being prepared; retry the same issue")
    validate_existing(repo, template, marker, config["private"])
    for attempt in range(30):
        branch = client.api("GET", endpoint + "/branches/main", missing_ok=True)
        if branch:
            break
        sleep(2)
    else:
        raise RuntimeError("Template generation is still in progress; retry the same issue")
    variable_path = endpoint + "/actions/variables/STUDENT_GITHUB"
    variable = client.api("GET", variable_path, missing_ok=True)
    if variable is None:
        try:
            client.api("POST", endpoint + "/actions/variables", {"name": "STUDENT_GITHUB", "value": login})
        except GitHubError as error:
            if error.status not in (409, 422):
                raise
        variable = client.api("GET", variable_path)
    if variable["value"].lower() != login.lower():
        raise ValueError("Repository is assigned to another student; nothing was overwritten")
    # Enable the inherited grader before granting student access.
    client.api("PUT", endpoint + "/actions/workflows/grade.yml/enable")
    if owner.lower() != login.lower():
        client.api("PUT", endpoint + "/collaborators/" + login, {"permission": "push"})
    # Generating from a template does not reliably cause a grading push event.
    client.api("POST", endpoint + "/actions/workflows/grade.yml/dispatches", {"ref": "main"})
    return "https://github.com/" + repository


def main():
    config = json.loads((ROOT / "course.json").read_text())
    validate_config(config)
    hub = config["owner"] + "/" + config["enroll_repo"]
    if os.environ.get("GITHUB_REPOSITORY", "").lower() != hub.lower():
        raise ValueError("Enrollment workflow must run in the configured enrollment repository")
    issue_client = GitHub(os.environ.get("ISSUE_TOKEN"))
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    if os.environ.get("GITHUB_EVENT_NAME") == "issues" and event.get("action") == "opened":
        # Fetch current author from GitHub; ignore account names supplied in form text.
        number = event["issue"]["number"]
    elif os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":
        value = os.environ.get("RETRY_ISSUE_NUMBER", "")
        if not re.fullmatch(r"[1-9][0-9]*", value):
            raise ValueError("Retry requires a positive issue number")
        number = int(value)
    else:
        raise ValueError("Only new enrollment issues or maintainer retries are accepted")
    endpoint = f"repos/{hub}/issues/{number}"
    issue = issue_client.api("GET", endpoint)
    try:
        login = parse_request(issue, config)
        url = provision(GitHub(os.environ.get("ENROLL_GITHUB_TOKEN")), config, login)
        body = (f"@{login}，你的 MuJoCo 学习仓库已准备好。\n\n"
                f"1. [接受邀请]({url}/invitations)（已有权限可直接打开）。\n"
                f"2. [进入个人仓库]({url})，按照 README 安装环境并完成 exercises。\n"
                f"3. push 到 main 后，在 [Actions]({url}/actions) 查看 **100 分制成绩**和评测日志。\n\n"
                "<!-- mujoco-enrollment:v1 -->")
        issue_client.api("POST", endpoint + "/comments", {"body": body})
        issue_client.api("PATCH", endpoint, {"state": "closed"})
        print("Enrollment complete: " + url)
    except (ValueError, RuntimeError, OSError, KeyError) as error:
        run_url = f"https://github.com/{hub}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}"
        print(redact(str(error)), file=sys.stderr)
        issue_client.api("POST", endpoint + "/comments", {
            "body": "本次领取未完成，申请保留。请维护者检查[运行日志](" + run_url +
                    ")，修正配置后用本 Issue 编号重试；已有练习不会被重置。"})
        raise


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError, KeyError) as error:
        sys.exit(redact(str(error)))
