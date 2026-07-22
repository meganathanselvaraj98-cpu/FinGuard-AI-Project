# System Architecture

```mermaid
flowchart LR
    U[Authenticated User] --> ST[Streamlit Website]
    A[Administrator] --> ST
    ST --> SVC[Python Service Layer]
    API[FastAPI JWT / Cookie API] --> SVC
    SVC --> SEC[AES-256-GCM + Argon2id]
    SVC --> ORM[SQLAlchemy ORM]
    ORM --> DB[(SQLite data/finguard_ai.db)]
    SVC --> ML[Scikit-learn / Joblib Models]
    SVC --> RP[CSV / Excel / PDF Reports]
    ST --> VIEW[My Stored Data / SQLite Viewer]
    VIEW --> ORM
```

SQLite runs in WAL mode with foreign keys, indexes, constraints, busy timeout and transaction rollback. Sensitive values are encrypted before SQLAlchemy writes them to SQLite.
