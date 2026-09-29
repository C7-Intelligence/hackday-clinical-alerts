# Getting Support

> Hack Day reference. Stuck on setup, or stuck mid-build? Start here.

Four ways to reach us, roughly in the order you should try them.

---

## 1. Check the docs first

Most setup problems have a known answer:

| Symptom | Where to look |
| --- | --- |
| `./run.sh` fails, port conflict, email verification stuck | [Installing DevKit.md § 6](<Installing DevKit.md>) |
| Anything else during install | [docs/troubleshooting.md](../docs/troubleshooting.md) — symptoms, causes, fixes |
| A Scope isn't showing up when filing a ticket | [Adding Providers.md](<Adding Providers.md>) |
| An MCP tool isn't being called | [Adding MCP Servers.md](<Adding MCP Servers.md>) |
| A Skill isn't firing | [Adding Skills.md](<Adding Skills.md>) |

---

## 2. Slack — fastest for a quick question

Join the Hack Day Slack community:

**<https://join.slack.com/t/hackday-brv1895/shared_invite/zt-4ar74ve28-YSK96VM1ERprQXoTIbTGBA>**

Best for short, specific questions — a command that failed, a field you're unsure about, a config that
won't take. Paste the actual error text; it's usually enough for someone to spot the problem
immediately.

> **Join before the day.** A Slack invite is a five-minute detour you don't want to be taking at 9am
> when you're trying to get unblocked.

---

## 3. Email — for anything longer

**hackday@duplocloud.net**

Better than Slack when the question needs context: a setup that fails in a way you can't summarize in a
line, a longer log, screenshots, or a question about whether your project idea is a good fit for the
platform.

---

## On the day

### The sponsor desk

**Our team is at the DuploCloud sponsor table all day.** Come find us if you're stuck, or if you just
want a second pair of eyes on an approach before you commit six hours to it.

This is the highest-bandwidth option by a wide margin. If something has eaten more than 15 minutes, walk
over.

### The Tech Spotlight talk

**A five-minute walkthrough on the main stage.** Worth catching if you want the whole picture — how the
platform fits together and what building an agent on it actually looks like — rather than a specific
answer.

---

## Helping us help you

Whichever channel you use, these make a fast answer much more likely:

- **The actual error text**, pasted — not a paraphrase
- **What you ran** — the command, or the click path through the UI
- **Where you are** — install, adding a provider, building the agent
- **What you already tried**

```bash
# Useful to include for anything install-related:
docker compose ps
docker --version && docker compose version && python3 --version
```

---

## Before you arrive

Get setup done at home, on home wifi — image pulls are slow on conference networks, and that's exactly
why it's homework.

- [ ] [Installing DevKit.md](<Installing DevKit.md>) complete, platform running
- [ ] Signed in at <http://localhost:4210>
- [ ] Joined the Slack community (link above)

**See you there.**
