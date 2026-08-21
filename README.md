# MemoPryl LPs · Standalone

2 LPs (ml05 + ml06) at root level. Subdomain routing via JS-based detection in root index.html.

## Structure

```
deploy-memopryl/
├── index.html              ← host router (auto-redirects to /ml05 or /ml06 on subdomain)
├── vercel.json
├── README.md
├── ml05/                    ← LP #1 (flat structure, no nested cc/pv4/...)
│   ├── index.html
│   └── assets/...
└── ml06/                    ← LP #2
    ├── index.html
    └── assets/...
```

## URLs

- `/` or `purelabs.com/` → host router index (links to both LPs)
- `/ml05` → ml05 LP
- `/ml06` → ml06 LP
- `ml05.purelabs.com/` → auto-redirects to `/ml05`
- `ml06.purelabs.com/` → auto-redirects to `/ml06`

## Deploy

1. Push to GitHub (already done: https://github.com/vsugamele/memopryl-lps)
2. Vercel auto-deploys
3. Add subdomains: ml05.purelabs.com + ml06.purelabs.com
4. DNS: CNAME each → cname.vercel-dns.com
