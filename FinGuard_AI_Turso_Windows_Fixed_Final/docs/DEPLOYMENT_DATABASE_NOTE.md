# Deployment Database Note

For local development, FinGuard AI uses SQLite automatically.

For a deployed shared application, **GitHub is not used as a live database**. GitHub stores code, not runtime user records.
To make all deployed users share one common data store, set `DATABASE_URL` to a **central managed database** in Streamlit secrets or environment variables.

Recommended deployment approach:

- GitHub: code repository only
- Streamlit: frontend hosting
- Managed database: shared persistent user data

This design ensures:

- all deployed users write to the same database
- all updates are reflected for the admin portal
- user details remain visible only inside the admin portal
- runtime data is not pushed back into GitHub automatically

## Example Streamlit secrets

```toml
DATABASE_URL = "postgresql+psycopg2://USER:PASSWORD@HOST:5432/DATABASE"
SECRET_KEY = "your-secret-key"
HASH_PEPPER = "your-hash-pepper"
FIELD_ENCRYPTION_KEY = "your-field-encryption-key"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Finguard@2026"
COOKIE_SECURE = true
```
