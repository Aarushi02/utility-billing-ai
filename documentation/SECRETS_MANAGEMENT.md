# Secrets Management — AWS SSM Parameter Store

All app secrets are stored in AWS SSM Parameter Store (free tier, encrypted).
No developer ever needs to share or manually copy a `.env` file again.

**AWS Account:** Troy & Banks — `335971291843`, region `us-east-2`
**Local credentials:** `~/.aws/credentials` [default] → Troy & Banks keys. No keys in `.env`.

---

## How It Works

```
Developer updates terraform.tfvars (gitignored)
        ↓
terraform apply → secrets pushed to SSM Parameter Store (encrypted)
        ↓
EC2 deploy: scripts/fetch_secrets.sh pulls SSM → writes .env
        ↓
docker compose up reads .env  (unchanged — no app code changes)
```

---

## Where Secrets Live

| Location | Purpose | Committed to git? |
|---|---|---|
| `terraform/terraform.tfvars` | Source of truth for secret values | No (gitignored) |
| AWS SSM Parameter Store | Encrypted storage in AWS | N/A |
| `.env` on EC2 | Generated automatically by fetch script | No |
| `.env` locally | For local dev only | No (gitignored) |

---

## SSM Parameter Path Structure

```
/utility-billing-ai/prod/DB_PASSWORD
/utility-billing-ai/prod/OPENAI_API_KEY
/utility-billing-ai/prod/DB_HOST
... etc
```

View in AWS Console:
```
AWS Console → Systems Manager → Parameter Store → Search: /utility-billing-ai/prod/
```

Or via CLI:
```bash
aws ssm get-parameters-by-path \
  --path "/utility-billing-ai/prod/" \
  --with-decryption \
  --region us-east-2 \
  --query "Parameters[*].[Name,Value]" \
  --output table
```

---

## Adding or Updating a Secret

1. Open `terraform/terraform.tfvars`
2. Find the `app_secrets` block
3. Add or update the key/value
4. Run:

```bash
cd terraform
terraform apply -auto-approve
```

That's it — SSM is updated immediately.

---

## New Developer Onboarding

A new developer needs:
1. AWS IAM credentials with SSM read access
2. Clone the repo
3. Run `scripts/fetch_secrets.sh` to generate their local `.env`

```bash
# One-time setup
aws configure   # enter their IAM access key + us-east-2

# Generate .env
chmod +x scripts/fetch_secrets.sh
./scripts/fetch_secrets.sh
```

No one emails/WhatsApps `.env` files anymore.

---

## EC2 Auto-Fetch on Every Boot (Lambda Start Included)

A systemd service (`utility-billing-startup.service`) is installed on EC2 and runs on every boot — including after the Lambda scheduler starts the instance each morning.

**Flow on every EC2 start:**
```
Lambda calls ec2:StartInstances
        ↓
EC2 boots → systemd starts utility-billing-startup.service
        ↓
fetch_secrets.sh → writes fresh .env from SSM (always latest credentials)
        ↓
docker compose up -d (api + streamlit + nginx start with current secrets)
```

Log file: `/var/log/fetch-and-start.log`

To manually trigger the same flow:
```bash
cd ~/utility-billing-ai
./scripts/fetch_secrets.sh
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

The EC2 IAM role already has `ssm:GetParametersByPath` permission (added via `terraform/secrets.tf`).
No AWS credentials needed on EC2 — IAM instance profile handles it automatically.

---

## IAM Permission Required (for developers)

Each developer IAM user needs this policy to read secrets locally:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "ssm:GetParameter",
      "ssm:GetParameters",
      "ssm:GetParametersByPath"
    ],
    "Resource": "arn:aws:ssm:us-east-2:*:parameter/utility-billing-ai/*"
  },
  {
    "Effect": "Allow",
    "Action": ["kms:Decrypt"],
    "Resource": "*"
  }]
}
```

---

## DB_URL — Not Stored in SSM

`DB_URL` is NOT a parameter in SSM. `src/utils/config.py` builds it at runtime from the individual parts:
- `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_PORT`, `DB_NAME`

Update only those five fields in `terraform.tfvars` — `DB_URL` is always correct automatically.

**Current production DB:** `database-1.cv8g6qea8dzl.us-east-2.rds.amazonaws.com`

---

## Files

| File | Purpose |
|---|---|
| `terraform/secrets.tf` | Creates SSM parameters via Terraform |
| `scripts/fetch_secrets.sh` | Pulls SSM params and writes `.env` on EC2 or locally |
| `scripts/fetch_and_start.sh` | Boot script: fetch secrets + start Docker Compose |
| `scripts/setup_autostart.sh` | Installs systemd boot service on existing EC2 |
| `terraform/terraform.tfvars` | Secret values (gitignored — never commit) |
