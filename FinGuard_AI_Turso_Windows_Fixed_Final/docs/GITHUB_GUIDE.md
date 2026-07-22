# GitHub Guide

```bash
git init
git add .
git commit -m "Build FinGuard AI secure finance intelligence platform"
git branch -M main
git remote add origin <your-repository-url>
git push -u origin main
```

Never commit `.env`, `.secrets/`, local databases, logs, generated user reports, or user-specific models. Bundled base Joblib artifacts and their evaluation metadata are intentionally tracked. Use dummy screenshots and dummy financial data only.
