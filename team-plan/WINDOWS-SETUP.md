# Windows setup (WSL2), for Stephen's demo machine

The DevKit's scripts are Linux shell, and its docs call native Windows "not verified". These are the steps
that got it running on Jason's Windows 11 laptop. **Do this before the day. The downloads take 20–40 minutes.**

1. **Install WSL2 + Ubuntu** from an **admin** terminal, then reboot:
   ```
   wsl --install -d Ubuntu
   ```
   After the reboot, Ubuntu opens and asks you to create a Linux username and password.

2. **Install Docker Desktop:**
   ```
   winget install -e --id Docker.DockerDesktop
   ```
   Open it and go to **Settings → Resources → WSL Integration**. Turn it on for **Ubuntu**.

3. **Start Docker Desktop.** It doesn't start with Windows by default, and the most common error
   (`docker compose (v2) — 'docker compose version' failed`) just means Docker Desktop isn't running.
   Check from the Ubuntu terminal:
   ```
   docker compose version && python3 --version
   ```
   Ubuntu already includes `python3`.

4. **Clone and run the DevKit inside Ubuntu**, in the Linux home folder (not `/mnt/c/...`, which is slow):
   ```
   git clone https://github.com/duplocloud/devkit ~/my-agent && cd ~/my-agent && ./run.sh
   ```
   - `Admin email:` must be a **work** email. It sends a verification link and waits up to 2 minutes.
   - It also prompts for an admin password and your LLM key.
   - Wait for `✔ Platform ready`, then sign in at http://localhost:4210 with that email and password.

5. **Check it:** `docker compose ps` shows all 6 services Up. Docker may mark `duplo-ai-studio` as
   "unhealthy" even when it works. On Jason's machine that was a false alarm, because the portal loaded
   and served requests fine.

6. **Install Claude Code inside Ubuntu** (so it sees the repo's `.claude/` commands):
   ```
   curl -fsSL https://claude.ai/install.sh | bash
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc
   cd ~/my-agent && claude
   ```
   The second line matters: without it you get `claude: command not found`. Sign in when prompted, then
   type `/duplo`, and `/duplo-extension` should appear. Always start `claude` from inside the repo folder.

7. **For the Neo4j seed loader:** Ubuntu's Python has no `venv` or `pip` by default, so run
   `sudo apt install -y python3-venv python3-pip`. Then `python3 -m venv .venv && .venv/bin/pip install neo4j`.

On the day, Stephen clones our team repo into Ubuntu (e.g. `~/hackday-clinical-alerts`) and runs
`./run.sh` there. If the `~/my-agent` stack is still running, run `./stop.sh` in it first so the ports are free.
