# DeepArk agent instructions

## Scope

Read README.md, CONTRIBUTING.md, OPERATIONS.md and docs/TESTING.md before work. Developer checkout paths are unrestricted. Use a separate checkout/worktree for concurrent tasks; never assume another developer's directory is disposable.

## Code and verification

- `plugin/` is the maintained companion source. Preserve the current AstrBot integration unless the task requires changing it.
- Run relevant tests; baseline offline command: `python3 -m unittest discover -s tests -v` from the repository root.
- Never glob-execute root scripts: some `container_*.py` call live providers; deployment scripts mutate production.
- Record the tested commit and actual command/results. Historical test reports are not fresh verification.
- `reference/` and `dafeiyu-config-pack/` are optional local references, not required dependencies.

## Production

- Existing connection: `ssh aliyun-ecs`; production is `/home/grainrain/astrbot`, not a development checkout.
- Routine development does not authorize deployment, configuration changes, restart, or live message sends. Follow the current task's explicit scope and existing session authorization.
- No separate test QQ is planned. Use synthetic inputs, fake sends and temporary storage. Do not connect test processes to production NapCat or duplicate the QQ login.
- Never print credentials or copy production credentials/chat databases into the repository or onto a developer's computer.
- Coordinate one production operator at a time. Back up affected state before authorized changes; keep code/config rollback separate from database restoration.
- Do not blindly rerun historical deploy/activate/rollback scripts. Inspect their fixed paths, assumptions and side effects first.

## Documentation

Update current operational facts when behavior changes. GOAL.md and historical records document previous work; their autonomous-work authorization does not authorize new work. Clearly distinguish proposed infrastructure from implemented infrastructure.
