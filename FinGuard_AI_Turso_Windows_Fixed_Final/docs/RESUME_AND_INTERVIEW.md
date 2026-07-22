# Resume Description and Interview Notes

## Resume description

Developed **FinGuard AI**, a secure multi-user personal-finance intelligence platform using Python, Streamlit, FastAPI, SQLAlchemy, and Turso Cloud with a local SQLite fallback. Implemented encrypted user profiles and bank accounts, Argon2id authentication, user-scoped transaction storage, bank-statement ingestion, interactive dashboards, budget and financial-health scoring, machine-learning predictions, anomaly detection, educational investment guidance, report exports, and a role-protected administrator analytics portal.

## Interview highlights

- Shared cloud records are stored in Turso and linked using unique `user_id` values.
- Normal users can query only their own records.
- Administrators can access cross-user analytics through role-protected routes.
- Sensitive profile and banking fields use AES-256-GCM encryption.
- Passwords use Argon2id hashing.
- The application supports local SQLite mode when cloud credentials are absent.
- The official `libsql` embedded-replica driver maintains a responsive local replica and synchronizes cloud changes.
