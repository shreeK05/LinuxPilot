# Filesystem Security

## Validation Flow
1. Target Path is received from Action Parameters.
2. Expands user (`~`).
3. Resolves to an absolute, canonical path (resolves symlinks and `..`).
4. Checks if the canonical path strictly resides inside one of the `allowed_roots`.
5. If invalid, throws `FilesystemSecurityError`.

## Protections
* **Path Traversal**: Mitigated by checking the resolved path against root directory.
* **Symlink Escapes**: Mitigated because `resolve()` evaluates symlinks before root containment checks.
