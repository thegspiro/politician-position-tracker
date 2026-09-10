"""Account management. Owners only, except for changing your own password."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import current_user, require_owner
from ..database import get_db
from ..models import ROLE_OWNER, User, new_user_uid
from ..passwords import hash_password, verify_password
from ..schemas import (
    PasswordChange,
    UserCreate,
    UserOut,
    UserUpdate,
)

router = APIRouter(prefix="/api/users", tags=["users"])


def _get_user(db: Session, uid: str) -> User:
    user = db.query(User).filter(User.uid == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _active_owner_count(db: Session, excluding: int | None = None) -> int:
    query = db.query(User).filter(User.role == ROLE_OWNER, User.is_active == 1)
    if excluding is not None:
        query = query.filter(User.id != excluding)
    return query.count()


@router.get("", response_model=list[UserOut])
def list_users(_owner: User = Depends(require_owner), db: Session = Depends(get_db)):
    return db.query(User).order_by(User.username).all()


@router.get("/me", response_model=UserOut)
def read_me(user: User = Depends(current_user)):
    return user


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    data: UserCreate,
    _owner: User = Depends(require_owner),
    db: Session = Depends(get_db),
):
    username = data.username.strip()
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="That username is already taken")

    user = User(
        uid=new_user_uid(),
        username=username,
        display_name=data.display_name,
        password_hash=hash_password(data.password),
        role=data.role,
        is_active=1 if data.is_active else 0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/{uid}", response_model=UserOut)
def update_user(
    uid: str,
    data: UserUpdate,
    owner: User = Depends(require_owner),
    db: Session = Depends(get_db),
):
    user = _get_user(db, uid)

    if data.username is not None:
        username = data.username.strip()
        clash = db.query(User).filter(User.username == username, User.id != user.id)
        if clash.first():
            raise HTTPException(status_code=400, detail="That username is already taken")
        user.username = username

    if data.display_name is not None:
        user.display_name = data.display_name

    # Losing the last owner would leave nobody able to manage accounts, so a
    # demotion or deactivation that would do so is refused.
    would_remove_owner = (
        data.role is not None and data.role != ROLE_OWNER and user.role == ROLE_OWNER
    ) or (data.is_active is False and user.role == ROLE_OWNER)
    if would_remove_owner and _active_owner_count(db, excluding=user.id) == 0:
        raise HTTPException(
            status_code=400,
            detail="This is the only owner account; promote another owner first",
        )

    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        if user.id == owner.id and not data.is_active:
            raise HTTPException(
                status_code=400, detail="You cannot deactivate your own account"
            )
        user.is_active = 1 if data.is_active else 0
    if data.password:
        user.password_hash = hash_password(data.password)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{uid}", status_code=204)
def delete_user(
    uid: str,
    owner: User = Depends(require_owner),
    db: Session = Depends(get_db),
):
    user = _get_user(db, uid)
    if user.id == owner.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    if user.role == ROLE_OWNER and _active_owner_count(db, excluding=user.id) == 0:
        raise HTTPException(
            status_code=400,
            detail="This is the only owner account; promote another owner first",
        )
    # Statements and sources keep their attribution: the foreign keys are
    # ON DELETE SET NULL, so the work survives the account.
    db.delete(user)
    db.commit()


@router.post("/me/password", status_code=204)
def change_own_password(
    data: PasswordChange,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your current password is incorrect",
        )
    user.password_hash = hash_password(data.new_password)
    db.commit()
