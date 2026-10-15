# Deploying the 360° Stock Analysis dashboard: GitHub → Cloud Build → Cloud Run

## Before you push to GitHub
- Use **only the files in this folder**. `app.py` is Upstox_Option_Chain_Dashboard_II_10 with the hard-coded Kite API key and the old commented-out token removed (the key now comes from the environment).
- Use this folder's `Zerodha_Generate_Access_Token.py` (credentials come from the environment). **Never commit your original copy.**
- Because the old values were already in your local files, **rotate** the Kite API secret / Zerodha password / TOTP secret and the old access token if the files were ever shared or pushed anywhere.
- `.gitignore` already blocks `.env`, `AccessToken/`, CSV/JSON/XLSX files.

```bash
git init && git add . && git commit -m "Dashboard deploy bundle"
git branch -M main && git remote add origin https://github.com/<you>/<repo>.git && git push -u origin main
```

## One-time GCP setup (replace PROJECT_ID; region asia-south1 is the default in cloudbuild.yaml)
```bash
gcloud config set project phrasal-fire-373510
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com

gcloud artifacts repositories create dashboards --repository-format=docker --location=asia-south1

# runtime service account
gcloud iam service-accounts create dashboard-runner
SA=dashboard-runner@phrasal-fire-373510.iam.gserviceaccount.com
gcloud projects add-iam-policy-binding phrasal-fire-373510 --member=serviceAccount:$SA --role=roles/bigquery.jobUser
gcloud projects add-iam-policy-binding phrasal-fire-373510 --member=serviceAccount:$SA --role=roles/bigquery.dataViewer
gsutil iam ch serviceAccount:$SA:objectAdmin gs://bba_access_token      # reads AND writes token files
gsutil iam ch serviceAccount:$SA:objectViewer gs://bba_support_files

# secret = your whole .env (Zerodha values from .env.example + the Upstox values you already use)
gcloud secrets create dashboard-env --data-file=.env
gcloud secrets add-iam-policy-binding dashboard-env --member=serviceAccount:$SA --role=roles/secretmanager.secretAccessor

# Cloud Build's service account needs to deploy and act as the runtime SA
PN=$(gcloud projects describe phrasal-fire-373510 --format='value(projectNumber)')
CB=$PN@cloudbuild.gserviceaccount.com      # or the trigger's own service account if you chose one
for R in roles/run.admin roles/artifactregistry.writer roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding phrasal-fire-373510 --member=serviceAccount:$CB --role=$R; done
gcloud iam service-accounts add-iam-policy-binding $SA --member=serviceAccount:$CB --role=roles/iam.serviceAccountUser
```
Update the secret later with `gcloud secrets versions add dashboard-env --data-file=.env` (redeploy to pick it up).

## Create the trigger
Cloud Console → Cloud Build → Triggers → Connect repository (GitHub) → Create trigger: event *Push to branch* `^main$`, configuration *Cloud Build configuration file* = `cloudbuild.yaml`. Override `_REGION`, `_AR_REPO`, `_SERVICE`, `_RUN_SA`, `_SECRET` as substitutions if you used other names.
Manual run: `gcloud builds submit --config cloudbuild.yaml .`

## Opening the dashboard (it is NOT public on purpose)
The app can generate broker tokens and place Zerodha alerts, so the service requires authentication.
- Quick: `gcloud run services proxy upstox-dashboard --region asia-south1 --port 8080` → http://localhost:8080
- Permanent: put it behind Identity-Aware Proxy (Cloud Run IAP), or grant `roles/run.invoker` to specific Google accounts.

## Things to know
- **Single instance, 1 worker.** Stream state, token globals and caches live in memory, so `max-instances=1` and gunicorn `--workers 1 --threads 8`. `min-instances=1` keeps it warm (small standing cost; set 0 to save money, state then resets after idle).
- **Slow cold start.** The app reads GCS/BigQuery and downloads the Upstox instruments file and NSE list at import; the 300 s timeout covers it.
- **Local CSV dropdown** scans the container's working directory, which is empty on Cloud Run (CSV files are excluded from the image). Use the BigQuery source there, or mount a GCS bucket and point `LOCAL_DATA_DIR` at it.
- **Token generation on Cloud Run** needs outbound internet (available by default) and the Upstox `.env` keys inside the secret. Upstox/Zerodha login may reject datacenter IPs; if the buttons fail, generate tokens elsewhere (they land in the same GCS bucket) and the dashboard picks them up.
- **Not tested here.** I couldn't run `docker build` or pip installs in my sandbox, so versions in `requirements.txt` are conservative ranges. If the build fails on a package, the Cloud Build log will name it; adjust that line.
