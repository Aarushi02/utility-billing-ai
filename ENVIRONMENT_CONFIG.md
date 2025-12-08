# Environment Configuration Guide

## How to Configure Environment Variables

Your application now works with **both local development (.env) and Streamlit Cloud (Secrets)**.

### For Local Development

1. Create a `.env` file in the project root:
   ```bash
   cp .env.example .env
   ```

2. Fill in your actual values in `.env`:
   ```env
   DB_TYPE=postgres
   DB_HOST=localhost
   DB_PORT=5432
   DB_USER=postgres
   DB_PASSWORD=your-password
   DB_NAME=utility_billing
   
   AWS_ACCESS_KEY_ID=your-access-key
   AWS_SECRET_ACCESS_KEY=your-secret-key
   AWS_BUCKET_NAME=utility-billing-data
   AWS_REGION=us-east-1
   
   OPENAI_API_KEY=your-openai-key
   OPENAI_MODEL=gpt-4o-mini
   
   AIRFLOW_API_URL=http://localhost:8080/api/v2
   AIRFLOW_API_USER=airflow
   AIRFLOW_API_PASSWORD=airflow
   ```

3. Run locally:
   ```bash
   streamlit run app/streamlit_app.py
   ```

### For Streamlit Cloud Deployment

1. Push your code to GitHub (without `.env` - it should be in `.gitignore`)

2. In **Streamlit Cloud Dashboard**:
   - Navigate to your app settings (⚙️ gear icon)
   - Click **"Secrets"**
   - Paste into the Secrets editor in TOML format:
   ```toml
   DB_TYPE = "postgres"
   DB_HOST = "your-host"
   DB_PORT = 5432
   DB_USER = "your-user"
   DB_PASSWORD = "your-password"
   DB_NAME = "your-db"
   
   AWS_ACCESS_KEY_ID = "your-key"
   AWS_SECRET_ACCESS_KEY = "your-secret"
   AWS_BUCKET_NAME = "utility-billing-data"
   AWS_REGION = "us-east-1"
   
   OPENAI_API_KEY = "your-key"
   OPENAI_MODEL = "gpt-4o-mini"
   
   AIRFLOW_API_URL = "http://localhost:8080/api/v2"
   AIRFLOW_API_USER = "airflow"
   AIRFLOW_API_PASSWORD = "airflow"
   
   ENV = "prod"
   ```

3. Click **"Save"** - changes take effect immediately

## How It Works

The `get_env()` helper function (added to key modules):
1. **First** checks Streamlit secrets (available on Cloud)
2. **Falls back** to environment variables or `.env` (local dev)
3. Returns a default if the key isn't found

This means:
- ✅ Local development uses `.env`
- ✅ Streamlit Cloud uses Secrets
- ✅ No code changes needed - same code works everywhere

## Important Notes

- **Never commit `.env`** to GitHub - it's in `.gitignore`
- **Secrets are encrypted** in Streamlit Cloud
- The **`get_env()` function** is safe to use in any module
- **AWS credentials** use `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` (uppercase with underscores)
- **Airflow variables** use standard naming: `AIRFLOW_API_URL`, `AIRFLOW_API_USER`, `AIRFLOW_API_PASSWORD`
- **Database** connection requires both `DB_HOST` and `DB_USER` with proper credentials
- Streamlit reloads automatically when secrets change (no redeployment needed)

## Troubleshooting

**"Missing API_KEY or DATABASE_URL" error?**
- Check that all required variables are in your secrets or `.env`
- On Streamlit Cloud: verify secrets are properly saved in the dashboard
- Locally: ensure `.env` file exists and is properly formatted

**Can't access secrets?**
- Ensure you're using the `get_env()` helper function
- The function gracefully handles missing secrets and falls back to `os.environ`
- Use correct variable names: `AWS_ACCESS_KEY_ID` (not `aws_access_key_id`)

**Database connection error?**
- Verify `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME` are correct
- For AWS RDS, ensure security groups allow your IP address
- Test connection: `psql -h {DB_HOST} -U {DB_USER} -d {DB_NAME}`

**Airflow API not responding?**
- Ensure `AIRFLOW_API_URL` is correct (e.g., `http://localhost:8080/api/v2`)
- Verify `AIRFLOW_API_USER` and `AIRFLOW_API_PASSWORD` are correct
- Check Airflow service is running: `airflow webserver --port 8080`

**OpenAI API key invalid?**
- Verify `OPENAI_API_KEY` is from https://platform.openai.com/api-keys
- Ensure key has not expired or been revoked
- Check correct model name: `gpt-4o-mini` (not `gpt-4`)
