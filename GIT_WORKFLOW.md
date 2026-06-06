## Git Workflow

For our group specific tasks we use a simple feature branch workflow.

### Branches

- `main`: stable/release branch. Only tested milestones are merged here.

- `dev`: integration branch. Completed features are merged here first.

- `feature/...`: task-specific branches created from `dev`.

- `fix/...`: branches for bug fixes.

- `docs/...`: branches for documentation changes.

- `practice/...`: personal learning branches. These are optional and are not part of the official project workflow.

### Workflow


1. Create a feature branch from `dev`.

   Example:

   ```bash
   git checkout dev
   git pull origin dev
   git checkout -b feature/docker-setup
   ```

2. Work on your task and push your changes.


   Example:

   ```bash
   git add .
   git commit -m "Add Docker setup"
   git push -u origin feature/docker-setup
   ```

3. Open Pull Request (PR) from the feature branch into `dev``.   

   Example:

   ```text
   feature/docker-setup → dev
   ```

4. Other team members review the pull request, test it locally, suggest improvements if needed and approve it.

5. After approval, merge the feature branch int `dev`. (Do not delete the branch, we will clean at the end of project).

6. When `dev` contains a tested and stable milestone, open a pull request from `dev`into `main`.

   Example:

   ```text
   dev → main
   ```

7. After final review and approval, merge `dev` into `main.

`main` should always contain the latest stable version of the project.

### Branch Naming Examples


```text
feature/docker-setup
feature/ci-cd
feature/kubernetes-setup
docs/git-workflow
fix/docker-compose-error
practice/andre/docker
```

### Practice Branches

Practice branches are optional and only used for personal learning or experiments.

Example:

```text
practice/andre/docker
practice/shabi/docker
practice/jonas/docker
```

Practice branches are not merged into `dev` or `main`.

The official project work should always happen in one task-specific feature branch, for example:

```text
feature/docker-setup
```

### General Flow

```text
feature/... → dev → main
```

