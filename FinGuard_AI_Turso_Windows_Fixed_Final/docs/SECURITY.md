# Security Design

- Argon2id password hashing
- AES-256-GCM field encryption
- Random nonce per encrypted value
- Runtime keys in `.secrets/`
- User-isolated queries and ownership checks
- Masked identifiers in UI, admin analytics and reports
- SQLite foreign keys and transactional rollback
- Login lock after repeated failures
- JWT bearer and HttpOnly-cookie API authentication
- Audit logging for security-relevant actions
- Database backups contain ciphertext and must remain private

The SQLite admin viewer always hides password and deterministic hash values. Raw storage mode may show AES ciphertext but never decrypts protected banking fields.
