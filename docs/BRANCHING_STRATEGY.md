## Branching Strategy

This repository uses a simple three-branch model:

- **`main`**: Stable, currently deployed 1.1 codebase.
- **`release/1.1-fallback`**: Permanent 1.1 maintenance branch for hotfixes and bug fixes.
- **`develop/2.0`**: Active 2.0 development branch containing all new 2.0 work.

### 1. Long‑lived branches

- **`main`**
  - Always releasable.
  - Only receives changes via pull requests (PRs).
  - May occasionally merge in approved fixes from `release/1.1-fallback`.

- **`release/1.1-fallback`**
  - Permanent branch tracking the latest 1.1 state.
  - Used exclusively for 1.1 bug fixes and hotfixes.
  - Never contains in‑progress 2.0 work.

- **`develop/2.0`**
  - Main integration branch for 2.0 work.
  - All 2.0 features and refactors are branched from and merged back into this branch.

### 2. 2.0 feature workflow

1. Start from `develop/2.0`:

   ```bash
   git switch develop/2.0
   git pull
   ```

2. Create a feature branch:

   ```bash
   git switch -c feature/2.0-<short-description>
   ```

3. Commit and push work:

   ```bash
   git add .
   git commit -m "feat(2.0): <description>"
   git push -u origin feature/2.0-<short-description>
   ```

4. Open a PR: `feature/2.0-…` → `develop/2.0`.

### 3. 1.1 bugfix workflow

1. Start from the permanent 1.1 branch:

   ```bash
   git switch release/1.1-fallback
   git pull
   ```

2. Create a 1.1 bugfix branch:

   ```bash
   git switch -c fix/1.1-<short-description>
   ```

3. Commit and push the fix:

   ```bash
   git add .
   git commit -m "fix(1.1): <what you fixed>"
   git push -u origin fix/1.1-<short-description>
   ```

4. Open a PR: `fix/1.1-…` → `release/1.1-fallback`.

5. After approval, merge back into `release/1.1-fallback` and push:

   ```bash
   git switch release/1.1-fallback
   git pull
   git merge --no-ff fix/1.1-<short-description>
   git push
   ```

### 4. Bringing 1.1 fixes into `main`

When a 1.1 fix has been validated in `release/1.1-fallback` and should also go to `main`:

```bash
git switch main
git pull
git merge --no-ff release/1.1-fallback
git push
```

### 5. Initial branch publication

If `release/1.1-fallback` and `develop/2.0` have not been pushed yet, publish them once after authenticating with GitHub:

```bash
git push -u origin release/1.1-fallback develop/2.0
```

