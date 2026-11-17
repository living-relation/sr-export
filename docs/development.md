# Development

**SR Export** is a Fusion add-in written in Python. This page covers how to work on the repository. Project layout, build steps, and tests are to be completed when the code lands.

## Repository status

The first commit is documentation only. Application code will arrive in a later pull request. Prefer adding code on a branch and opening a PR, rather than committing straight to `main`, once this repository is in use.

## Clone

Clone the public repository and work in your local copy:

```
git clone https://github.com/living-relation/sr-export.git
```

Load that local copy into Fusion as described in [Install](install.md).

## Layout

Expected folders and the add-in entry point and manifest are to be completed when the code lands.

## Coding notes

- This repository is public. Do not commit secrets, tokens, passwords, personal email addresses, or machine-specific paths.
- Keep Spark Robotic / SR- naming in user-visible text and repository docs.
- Match the style of the code when it lands. Language, API, and lint details are to be completed when the code lands.

## Tests

How to run tests, including any checks that must run inside Fusion, is to be completed when the code lands.

## Contributing

1. Open an issue or draft a short plan for the change if the work is larger than a small fix.
2. Create a branch from `main`.
3. Add or update documentation in `docs/` when behavior changes.
4. Open a pull request against `main`.

Review and CI expectations are to be completed when the code lands.
