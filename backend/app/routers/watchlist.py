from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_admin
from app.models import User, WatchlistEntry
from app.schemas import WatchlistCreate, WatchlistOut, WatchlistUpdate
from app.services import audit

router = APIRouter(prefix="/api/v1/watchlist", tags=["watchlist"])


@router.get("", response_model=list[WatchlistOut])
async def list_watchlist(
    category: str | None = Query(default=None),
    q: str | None = Query(default=None),
    active_only: bool = Query(default=True),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[WatchlistOut]:
    query = db.query(WatchlistEntry)
    if active_only:
        query = query.filter(WatchlistEntry.is_active.is_(True))
    if category:
        query = query.filter(WatchlistEntry.category == category)
    if q:
        like = f"%{q}%"
        query = query.filter((WatchlistEntry.identifier_value.ilike(like)) | (WatchlistEntry.label.ilike(like)))
    return query.order_by(WatchlistEntry.created_at.desc()).all()


@router.post("", response_model=WatchlistOut, status_code=status.HTTP_201_CREATED)
async def create_watchlist_entry(
    payload: WatchlistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> WatchlistOut:
    existing = (
        db.query(WatchlistEntry)
        .filter(
            WatchlistEntry.identifier_type == payload.identifier_type,
            WatchlistEntry.identifier_value == payload.identifier_value,
            WatchlistEntry.is_active.is_(True),
        )
        .first()
    )
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "An active watchlist entry with this identifier already exists")

    entry = WatchlistEntry(**payload.model_dump(), created_by=current_user.id)
    db.add(entry)
    db.commit()
    db.refresh(entry)

    audit.record(
        db,
        actor=current_user,
        action="watchlist.create",
        entity_type="watchlist_entry",
        entity_id=entry.id,
        details={"identifier_value": entry.identifier_value, "category": entry.category.value},
    )
    return entry


@router.patch("/{entry_id}", response_model=WatchlistOut)
async def update_watchlist_entry(
    entry_id: str,
    payload: WatchlistUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> WatchlistOut:
    entry = db.query(WatchlistEntry).filter(WatchlistEntry.id == entry_id).first()
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Watchlist entry not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(entry, field, value)
    db.add(entry)
    db.commit()
    db.refresh(entry)

    audit.record(
        db,
        actor=current_user,
        action="watchlist.update",
        entity_type="watchlist_entry",
        entity_id=entry.id,
        details={"fields": list(updates.keys())},
    )
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_watchlist_entry(
    entry_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
) -> None:
    entry = db.query(WatchlistEntry).filter(WatchlistEntry.id == entry_id).first()
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Watchlist entry not found")
    entry.is_active = False
    db.add(entry)
    db.commit()

    audit.record(db, actor=current_user, action="watchlist.deactivate", entity_type="watchlist_entry", entity_id=entry.id)
