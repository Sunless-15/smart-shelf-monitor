# Permanent Agent Rules

1. **Session Start**: At the START of every session, read `PROGRESS.md` and `AGENT_RULES.md` before doing anything else.
2. **Frequent Updates**: Update `PROGRESS.md` after EVERY meaningful step: after finishing a file, a feature, a fix, or a test run. Never batch updates for the end, because the session can be cut off at any moment.
3. **Task Tracking**: Before starting any task, write it under "Current task" first. When finished, move it to the "Completed work log" and update "Next steps".
4. **Precision**: Keep "Current task" precise enough that someone with zero memory could continue mid-task.
5. **Issue Tracking**: Record every error that is not yet fixed under "Known issues".
6. **Git Commits**: Make a git commit after each completed task with a clear message (initialize git if it isn't already). Run `git add -A && git commit -m "<message>"`.
7. **Verification**: Never mark something DONE unless it has been run or tested and works.
8. **Graceful Limits**: If you are about to hit a limit or are warned about one, immediately update `PROGRESS.md` with the exact stopping point and commit.
9. **History Preservation**: Never delete or rewrite history in `PROGRESS.md`. Only append to the log and update the status sections.
10. **Explain Document Updates**: Update `docs/PROJECT_EXPLAINED.md` whenever `PROGRESS.md` is updated for a completed task. Every claim in it must be verified against the code or logs.
