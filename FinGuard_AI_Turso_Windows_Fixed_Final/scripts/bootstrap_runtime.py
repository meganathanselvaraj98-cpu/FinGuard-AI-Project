"""Create local SQLite runtime directories and non-committed secrets."""
from backend.config import get_field_encryption_key, settings
from backend.database import initialize_database

for directory in (
    settings.data_dir,
    settings.backup_dir,
    settings.secret_dir,
    settings.log_dir,
    settings.model_dir,
    settings.user_model_dir,
    settings.report_dir,
):
    directory.mkdir(parents=True, exist_ok=True)
get_field_encryption_key()
initialize_database()
print(f"FinGuard database is ready in {settings.database_mode} mode")
