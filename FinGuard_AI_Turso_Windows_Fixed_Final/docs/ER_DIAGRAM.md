# Database ER Diagram

```mermaid
erDiagram
  USERS ||--o| USER_PROFILES : has
  USERS ||--o| USER_PREFERENCES : configures
  USERS ||--o{ BANK_ACCOUNTS : owns
  USERS ||--o{ STATEMENT_IMPORTS : uploads
  USERS ||--o{ TRANSACTIONS : owns
  USERS ||--o{ BUDGETS : creates
  USERS ||--o{ PREDICTIONS : receives
  USERS ||--o{ REPORTS : generates
  USERS ||--o{ AUDIT_LOGS : produces
  BANK_ACCOUNTS ||--o{ STATEMENT_IMPORTS : groups
  BANK_ACCOUNTS ||--o{ TRANSACTIONS : contains
  STATEMENT_IMPORTS ||--o{ TRANSACTIONS : imports
  CATEGORIES ||--o{ TRANSACTIONS : classifies
```

Sensitive values are stored in AES-256-GCM encrypted text columns. Last-four digits and deterministic hashes support masking and duplicate checks without displaying original identifiers. Foreign keys use cascade or set-null behaviour to preserve relational integrity.
