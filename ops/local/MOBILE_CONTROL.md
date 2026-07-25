# Pegasus mobile control

This folder lets the Pegasus computer receive approved operations from the GitHub mobile app.

## One-time activation

1. In GitHub, open the Pegasus repository settings.
2. Open Actions, then Runners, then create a new self-hosted runner for Windows.
3. Copy the repository URL and short-lived registration token shown by GitHub.
4. Run `install-github-runner.ps1` with these two values.
5. Keep the runner window active while first testing it. It can later be installed as a Windows service if administrative access is available.

## Mobile usage

Open GitHub mobile, choose Actions, select `Pegasus Local Operations`, press Run workflow, and choose:

- `health`: checks the local API.
- `daily-refresh`: imports and validates the daily racing program.
- `reconcile-results`: continues official-result reconciliation from its checkpoint.
- `model-report`: reads the conservative model safety state.

The local computer must be powered on and connected to the internet. Operations do not publish betting claims; safety gates remain authoritative.