# Contributing to Map to GeoJSON Converter

Thank you for your interest in contributing! This project is open-source and student-friendly. We welcome all contributions, big or small.

## How to Contribute

### 1. Report Issues

- Open an issue on GitHub with a clear title and description.
- Include steps to reproduce, sample images, and expected output.
- Use the issue templates (`bug`, `feature`, `tech-debt`) and apply:
  - one `type:*` label
  - one `area:*` label
  - one `prio:*` label
- Assign a roadmap milestone (`M1` to `M4`) before moving work to ready state.

### 2. Suggest Features

- Check existing issues first.
- Open a feature request with details on why it's useful.
- Add acceptance criteria so the issue can be planned on the board.

### 3. Code Contributions

- Fork the repo and create a branch for your changes.
- Follow Python best practices (PEP 8).
- Add tests for new features.
- Update documentation if needed.
- Keep new behavior backward-compatible by default and expose opt-in switches for risky changes.

### 4. Pull Requests

- Ensure your code passes any existing tests.
- Provide a clear description of changes.
- Reference related issues (`Closes #123`).
- Follow `.github/pull_request_template.md`.
- Ensure issue/PR PM metadata is complete before requesting review.

## PM Workflow (GitHub Projects centered)

This repository uses a board-driven execution model.

- **Board columns:** `Backlog` -> `Ready` -> `In Progress` -> `In Review` -> `Done`
- **Ready criteria:** labels + milestone + clear acceptance criteria
- **In Review trigger:** linked PR is opened
- **Done criteria:** PR merged and verification complete

Full operating guide: `docs/PROJECT _MANAGEMENT/GITHUB_PROJECTS_WORKFLOW.md`

### Bootstrap labels and milestones

Preferred:

`python scripts/bootstrap_github_pm.py`

If `gh` is not authenticated, run:

`gh auth login`

## Development Setup

1. Clone the repo: `git clone https://github.com/ironn0/Map_to_Geojson-Converter.git`
2. Install dependencies: `pip install -r requirements-dev.txt`
3. Run quality + tests + benchmark checks: `python scripts/verify.py`
5. Test your changes locally.

## Code Style

- Use 4 spaces for indentation.
- Write clear, commented code.
- Keep functions small and focused.

## Community

- Be respectful and constructive.
- For questions, use GitHub Discussions.

We appreciate your help in making geospatial data accessible to everyone!