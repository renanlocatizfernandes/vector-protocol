# Versioning Strategy

This project follows [Semantic Versioning 2.0.0](https://semver.org/).

## Format
`MAJOR.MINOR.PATCH`

- **MAJOR**: Incompatible API changes or significant architecture shifts.
- **MINOR**: Backward-compatible functionality (new features).
- **PATCH**: Backward-compatible bug fixes.

## Branching Model

We follow a simplified Git Flow:

- **`main`**: Production-ready code. Always stable.
- **`feature/foo-bar`**: New features. Merge into `main` via PR.
- **`fix/bug-name`**: Bug fixes. Merge into `main` via PR.
- **`docs/update-name`**: Documentation only changes.
- **`refactor/component-name`**: Code improvements without logic change.

## Tagging
Release versions should be tagged in git:
```bash
git tag v1.0.0
git push origin v1.0.0
```
