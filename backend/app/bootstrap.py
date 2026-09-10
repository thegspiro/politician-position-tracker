"""Create the first owner account on a fresh install.

Run once at container start, after migrations. ADMIN_PASSWORD seeds the owner
so a new deployment is never reachable without a login. Once any account
exists this does nothing, and ADMIN_PASSWORD stops being accepted at login --
so the shared credential exists only for as long as it takes to create the
account that replaces it.
"""

import logging
import sys

from .auth import ADMIN_PASSWORD, ADMIN_USERNAME
from .database import SessionLocal
from .models import ROLE_OWNER, User, new_user_uid
from .passwords import hash_password

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def bootstrap_owner() -> bool:
    """Create the owner account if there are no accounts. Returns True if created."""
    db = SessionLocal()
    try:
        if db.query(User.id).first() is not None:
            logger.info("Accounts already exist; skipping bootstrap.")
            return False

        if not ADMIN_PASSWORD:
            logger.warning(
                "No accounts exist and ADMIN_PASSWORD is unset, so no owner "
                "account can be created. Set ADMIN_PASSWORD and restart."
            )
            return False

        user = User(
            uid=new_user_uid(),
            username=ADMIN_USERNAME,
            display_name="Administrator",
            password_hash=hash_password(ADMIN_PASSWORD),
            role=ROLE_OWNER,
            is_active=1,
        )
        db.add(user)
        db.commit()
        logger.info(
            "Created owner account %r from ADMIN_PASSWORD. That password now "
            "works only through this account; change it in the admin panel.",
            ADMIN_USERNAME,
        )
        return True
    finally:
        db.close()


def main() -> int:
    bootstrap_owner()
    return 0


if __name__ == "__main__":
    sys.exit(main())
