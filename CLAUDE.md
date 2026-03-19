# brianborg-website

## Project Overview
Personal website for Brian Borg — Founder & CEO of OnPath Testing, based in Boulder, CO.

## Development Standards
- Every change must include unit tests
- CI must enforce coverage threshold
- Never commit secrets, API keys, or credentials
- Keep code simple — no over-engineering or premature abstractions
- Use conventional commits (feat:, fix:, docs:, etc.)

## Workflow
- "Ship it" or "tk" = confirmed, proceed with full workflow (PR, CI, merge, cleanup)
- After shipping features, prompt to update GitHub Issues if applicable
- All Claude Code memory/config edits can be made without asking permission

## Tech Stack
- **Framework:** Astro (static site generation)
- **Styling:** Tailwind CSS v4
- **Hosting:** Netlify (auto-deploys from GitHub `main` branch)
- **Domain:** brianborg.com (registered on Cloudflare, DNS points to Netlify)

## Commands
- `npm run dev` — local dev server
- `npm run build` — production build to `dist/`
