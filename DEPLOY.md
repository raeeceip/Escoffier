# MasterChef-Bench Deployment Guide (Linode + Kamal)

> 🚀 This document explains, **step-by-step**, how to turn a blank Ubuntu 22.04 Linode into a production instance running the full MasterChef-Bench monorepo (backend API, CLI, LLM playground, metrics and Traefik) with [Kamal](https://kamal-deploy.org).
>
> _Approximate wall-clock time_: **15 minutes**.

---

## 0. Pre-requisites

| Item                   | Details                                                                                 |
| ---------------------- | --------------------------------------------------------------------------------------- |
| **Local workstation**  | macOS / Linux with Docker 24+, Go 1.22+, Ruby 3.2+                                      |
| **Kamal**              | `gem install kamal` (≥ 1.4)                                                             |
| **Container registry** | GHCR (GitHub Packages), ECR or Docker Hub                                               |
| **Linode**             | 1 × Nanode (1 vCPU / 2 GB) is enough for demo; create a fresh Ubuntu 22.04 LTS instance |

> **Naming convention used below**  
> Replace the placeholders:
>
> - `me@example.com` – your email
> - `my-gh-user` – your GitHub username or registry namespace
> - `linode-ip` – public IPv4 of the Linode
> - `deploy` – remote user (created in step 2)
>
> All commands are run from the repository root unless noted.

---

## 1. Generate and store API tokens

| Token                     | Where to create                                        | Scope                        | Where to save                                                                                 |
| ------------------------- | ------------------------------------------------------ | ---------------------------- | --------------------------------------------------------------------------------------------- |
| `OPENAI_API_KEY`          | <https://platform.openai.com/account/api-keys>         | `tts:all, models:read`       | GitHub → _Settings → Secrets → Actions_                                                       |
| `ANTHROPIC_API_KEY`       | <https://console.anthropic.com/settings/keys>          | _default_                    | GitHub Secrets                                                                                |
| `GOOGLE_API_KEY`          | Google Cloud Console → AI Studio credentials           | Vertex `generative-language` | GitHub Secrets                                                                                |
| `KAMAL_REGISTRY_PASSWORD` | Personal access token (GHCR) **with `write:packages`** | push images                  | GitHub Secrets                                                                                |
| `DEPLOY_KEY` (SSH)        | `ssh-keygen -t ed25519 -C kamal`                       | N/A                          | ① add _public_ key to `~/.ssh/authorized_keys` on Linode ② add _private_ key to GitHub Secret |

Export them locally while testing:

```bash
export OPENAI_API_KEY="sk-…"
export ANTHROPIC_API_KEY="sk-…"
export GOOGLE_API_KEY="…"
export KAMAL_REGISTRY_PASSWORD="ghp_…"
```

---

## 2. Prepare the Linode host

```bash
ssh root@linode-ip
# 1 ) system updates & Docker
apt update && apt upgrade -y
apt install -y docker.io docker-compose
usermod -aG docker root  # keep simple – we'll use root for demo
# 2 ) Ruby & Kamal
apt install -y ruby-full build-essential
gem install kamal --no-document
exit
```

Create a non-root user (optional but recommended):

```bash
ssh root@linode-ip "useradd -m -s /bin/bash deploy && usermod -aG docker deploy"
# copy your SSH public key
ssh-copy-id deploy@linode-ip
```

---

## 3. Add Kamal configuration to the repo

A starter `kamal.yml` was generated earlier – double-check:

```yaml
service: masterchef
image: ghcr.io/my-gh-user/masterchef-bench
servers:
  - deploy@linode-ip
registry:
  server: ghcr.io
  username: my-gh-user
  password:
    - KAMAL_REGISTRY_PASSWORD
volumes:
  - "/srv/masterchef/data:/app/data"
env:
  clear:
    PORT: "8080"
    PLAYGROUND_PORT: "8090"
  secret:
    - OPENAI_API_KEY
    - ANTHROPIC_API_KEY
    - GOOGLE_API_KEY
    - DATABASE_URL
traefik:
  enabled: true
  host_port_http: 80
  host_port_https: 443
  letsencrypt_email: me@example.com
```

Commit the file:

```bash
git add kamal.yml
git commit -m "infra: add Kamal config"
```

---

## 4. First-time deploy from laptop

```bash
# Build container image
kamal build
# Push to GHCR (auth uses KAMAL_REGISTRY_PASSWORD)
kamal push
# Upload secrets (.env) and Traefik cert store
kamal env push
# Boot the stack
kamal deploy
```

You should see Traefik, the app container and a persistent volume under `/srv/masterchef/data` on the Linode. Browse to `http://linode-ip` → the `/health` endpoint returns JSON.

---

## 5. GitHub Actions CI/CD (optional)

Add `.github/workflows/deploy.yml`:

```yaml
name: Deploy
on: [push]
jobs:
  deploy:
    runs-on: ubuntu-latest
    env:
      KAMAL_REGISTRY_PASSWORD: ${{ secrets.KAMAL_REGISTRY_PASSWORD }}
      OPENAI_API_KEY:          ${{ secrets.OPENAI_API_KEY }}
      ANTHROPIC_API_KEY:       ${{ secrets.ANTHROPIC_API_KEY }}
      GOOGLE_API_KEY:          ${{ secrets.GOOGLE_API_KEY }}
      DATABASE_URL:            ${{ secrets.DATABASE_URL }}
    steps:
      - uses: actions/checkout@v4
      - uses: ruby/setup-ruby@v1
        with: { ruby-version: 3.2 }
      - run: gem install kamal
      - name: Build & deploy
        env: { SSH_PRIVATE_KEY: ${{ secrets.DEPLOY_KEY }} }
        run: |
          eval $(ssh-agent)
          echo "$SSH_PRIVATE_KEY" | tr -d '\r' | ssh-add -
          kamal build && kamal push && kamal deploy
```

Every push to `main` triggers a zero-downtime rolling update.

---

## 6. Useful Kamal commands

| Command                      | Purpose                       |
| ---------------------------- | ----------------------------- |
| `kamal exec app bin/rails c` | SSH into running container    |
| `kamal logs -f`              | Tail application logs         |
| `kamal redeploy`             | Build new image & roll update |
| `kamal rollback`             | Revert to previous release    |
| `kamal env pull`             | Download live `.env`          |

---

## 7. Troubleshooting checklist

1. **Container won't start** → `kamal logs` and `docker logs` on host.
2. **TLS not issued** → ports 80/443 must be open; domain must resolve to Linode IP.
3. **Image push denied** → PAT needs `write:packages` on GHCR.

---

## 8. Next steps

- Scale horizontally: add more IPs under `servers:` then `kamal redeploy`.
- Add Postgres instead of SQLite – declare another service in `kamal.yml`.
- Create Grafana dashboards on port 3000 (Traefik can route).

Happy cooking 🧑‍🍳🍲
