# Skills

A collection of agent skills I have built for specific workflows.

Each skill captures reusable instructions, conventions, and supporting resources
for a focused task. The goal is to make workflows repeatable, easy to share, and
simple to improve over time.

## Repository structure

Each skill lives in its own directory:

```text
skill-name/
├── SKILL.md
├── scripts/      # Optional automation
├── references/   # Optional supporting documentation
└── assets/       # Optional templates and other resources
```

`SKILL.md` describes when to use the skill and how an agent should follow its
workflow. Supporting directories are included only when the skill needs them.

## Using a skill

Clone the repository, then copy or link the skill directory into the skills
directory used by your agent:

```bash
git clone git@github.com:anovoselnik/skills.git
```

Consult the skill's `SKILL.md` for any setup requirements or usage notes.
