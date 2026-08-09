# Day 0 — Zerops checklist

## Account setup
1. Register: https://www.wemakedevs.org/hackathons/zerops#register
2. Create Zerops account ($15 free credits)
3. Copy API token to `.env` as `ZEROPS_API_TOKEN`

## Manual Zerops spike (do once)
```bash
# Install zcli — see https://docs.zerops.io/references/zcli
zcli login
zcli project service-import zerops/import-deplot-services.yaml -P YOUR_PROJECT_ID
```

## Curated demo repositories
| Repo | Stack | Demo use |
|------|-------|----------|
| TBD Next.js + Prisma | nextjs, postgres | Primary happy path |
| TBD FastAPI API | fastapi, postgres | Secondary stack |

Replace TBD with public repos before hackathon start.

## Deplot on Zerops
Deploy using files in `zerops/` and **`zerops.yaml` at repo root** (required for GitHub CI/CD):
- `zerops.yaml` — build config for **web** + **api** (must be at repository root)
- `import-deplot-services.yaml` — provisions postgres, api, web
- `zerops-api.yaml` / `zerops-web.yaml` — reference copies (optional)
