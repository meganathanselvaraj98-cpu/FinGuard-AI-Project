"""Print a URL-safe 256-bit key suitable for FIELD_ENCRYPTION_KEY."""
import base64
import os
print(base64.urlsafe_b64encode(os.urandom(32)).decode("ascii"))
