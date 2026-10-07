# MuJoCo 个人学习仓库领取

课程：**MuJoCo 从零到开发代码阅读**。14 章、50 组练习、200 项检查，总分 100 分。
从 Python/NumPy 与 MJCF 基础，逐步学习状态、控制、动力学、传感器、渲染、环境封装和 C++ API。

## 领取步骤

1. 登录你自己的 GitHub 账号，点击本仓库的 **Issues → New issue → 领取 MuJoCo 学习仓库**。
2. 选择课程并创建 Issue，无需填写 Token、密码或其他人的账号。
3. 等待机器人回复，接受仓库邀请。
4. 打开回复中的 `mujoco-learning-你的账号`，按照 README 开始练习。
5. 提交到个人仓库的 `main` 分支，在 Actions 查看分数和失败日志。

领取入口：[提交申请](https://github.com/ZhenyuYangK/mujoco-enroll/issues/new?template=enroll.yml)。同一账号再次申请会复用仓库，不覆盖已完成的作业。

## 维护者初始化

本仓库的 `course.json` 默认对应：

| 配置 | 值 |
| --- | --- |
| owner | ZhenyuYangK |
| 模板仓库 | mujoco-learning-template |
| 个人仓库前缀 | mujoco-learning |
| 可见性 | public |
| 提交分支 | main |

1. 在同一账号或组织发布练习模板，默认分支设为 `main`，启用 **Settings → Template repository**。
2. 在本仓库 **Settings → Secrets and variables → Actions → New repository secret** 添加 `ENROLL_GITHUB_TOKEN`。
3. 该凭据需要在目标账号创建仓库、生成模板仓库、管理协作者、写入 Actions variables、启用和触发 workflow。使用 GitHub App 时安装范围必须覆盖新创建的仓库。个人账号快速试用可以使用 classic PAT 的 `repo`、`workflow` 权限；仅配置在领取仓库，不能配置在练习仓库。
4. 确保两个仓库都允许运行 GitHub Actions。
5. 提交一个领取 Issue，确认回复的仓库中存在 `STUDENT_GITHUB` 变量，且 Actions 已开始初始评测。

机器人从 **Issue 作者**获取身份，不使用正文填写的账号。新仓库由模板生成，已有仓库必须匹配模板来源、学习者标记和可见性，遇到冲突停止处理。

## 重试与排错

领取失败时保留 Issue。维护者在 **Actions → 领取 MuJoCo 学习仓库 → Run workflow** 输入 Issue 编号重试。
模板生成与 GitHub 请求可能暂时不可用，重试会检查已有仓库后继续配置，不会重新生成作业。

如没有触发流程，检查 Actions 是否启用、是否使用模板提交 Issue；如创建后失败，检查 Token 的变量管理、协作者管理和 Actions 写入权限。若模板的默认分支不是 main，请先修正模板。

本仓库只处理领取；个人仓库中每次 push 运行评分。100 分不代表自动向 OpenCamp 上传成绩。

旧标题“MuJoCo 基础与机器人仿真”的申请仍可重试。新领取使用扩充后的模板；已经领取的旧个人仓库不会因模板更新自动改变作业，升级前应保留已完成的 ex01–ex10。

```bash
python3 -m unittest discover -s tests -v
```
