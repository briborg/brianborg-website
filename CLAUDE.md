# brianborg-website

## Project Overview
Personal website for Brian Borg — Founder & CEO of OnPath Testing, based in Boulder, CO.

## Shared development workflow

The single maintained `/dev` source is `onpathtesting/onpath-org`, `operations/skills/dev`. Resolve an explicitly configured `ONPATH_ORG_ROOT` first; an invalid configured root blocks work rather than falling back. Otherwise resolve the installed `/dev` entry point or Brian's checkout at `/Users/brianborg/Projects/onpathtesting/onpath-org/operations/skills/dev`. Before using it, verify `SKILL.md` contains `Canonical workflow: onpathtesting/onpath-org — operations/skills/dev.`, resolve and read its required references, and verify installed client entry points resolve consistently to that source. An old readable skill copy is not an acceptable fallback. If the canonical source/references cannot be verified, report the blocker; do not silently skip the workflow. Record the resolved source/revision in the work record.

Follow that workflow for agent-owned preparation, complete ticket Testing, bounded execution, independent review, authority and delivery lifecycle; retain all project gates below. Do not close tickets merely on main merge or infer human QA. The standalone Bounded Development pilot remains opt-in. Project shorthand confirms only its actual proposed action.

## Development Standards
- Include applicable unit/regression tests for changed behavior; preserve required tests and coverage gates. Instruction-only changes use focused source review and checks rather than meaningless application tests
- CI must enforce coverage threshold
- Never commit secrets, API keys, or credentials
- Keep code simple — no over-engineering or premature abstractions
- Use conventional commits (feat:, fix:, docs:, etc.)

## Workflow
- "Ship it" or "tk" = confirmed, proceed with the proposed full workflow (PR, CI, merge, cleanup), preserving this project convention. Apply the confirmation to the actual proposed effort; do not infer unrelated production authority. Main is documented as auto-deploying to Netlify, so establish that consequence and applicable production authority before an authorized merge
- Agents maintain the required issue and Testing evidence automatically; distinguish main merge, verified production delivery and human QA
- All Claude Code memory/config edits can be made without asking permission

## Tech Stack
- **Framework:** Astro (static site generation)
- **Styling:** Tailwind CSS v4
- **Hosting:** Netlify (auto-deploys from GitHub `main` branch)
- **Domain:** brianborg.com (registered on Cloudflare, DNS points to Netlify)

## Commands
- `npm run dev` — local dev server
- `npm run build` — production build to `dist/`
