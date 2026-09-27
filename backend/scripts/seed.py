import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, SessionLocal, engine
from app.models import (
    AlertSeverity,
    Camera,
    CameraStatus,
    IdentifierType,
    SourceProtocol,
    StorageTier,
    User,
    UserRole,
    WatchlistCategory,
    WatchlistEntry,
)
from app.security import encrypt_secret, hash_password

CAMERAS = [
    dict(
        id="C001",
        name="Ahmedabad Ring Road Junction",
        department="Ahmedabad Traffic Police",
        zone="Zone-1-Ahmedabad",
        camera_type="fixed",
        latitude=23.0225,
        longitude=72.5714,
        source_protocol=SourceProtocol.simulator,
        stream_ref="simulator:C001:Ahmedabad Ring Road Junction",
        storage_tier=StorageTier.hot,
        retention_days=30,
    ),
    dict(
        id="C002",
        name="Gandhinagar RTO Checkpoint",
        department="Gandhinagar RTO",
        zone="Zone-2-Gandhinagar",
        camera_type="fixed",
        latitude=23.2156,
        longitude=72.6369,
        source_protocol=SourceProtocol.file,
        stream_ref="file:media/sample/checkpoint.mp4",
        storage_tier=StorageTier.hot,
        retention_days=30,
    ),
    dict(
        id="C003",
        name="Surat Highway Toll Plaza",
        department="Surat Traffic Police",
        zone="Zone-3-Surat",
        camera_type="fixed",
        latitude=21.1702,
        longitude=72.8311,
        source_protocol=SourceProtocol.simulator,
        stream_ref="simulator:C003:Surat Highway Toll Plaza",
        storage_tier=StorageTier.warm,
        retention_days=45,
    ),
    dict(
        id="C004",
        name="Vadodara Old Bypass Camera",
        department="Vadodara Traffic Police",
        zone="Zone-4-Vadodara",
        camera_type="fixed",
        latitude=22.3072,
        longitude=73.1812,
        source_protocol=SourceProtocol.file,
        # Intentionally points at a feed that was never uploaded, so the
        # heartbeat service's health check genuinely reports it Offline --
        # this is here on purpose, to show that camera health is derived
        # from a real check rather than hard-coded.
        stream_ref="file:media/sample/decommissioned_feed.mp4",
        storage_tier=StorageTier.cold,
        retention_days=90,
    ),
    dict(
        id="C005",
        name="Rajkot Border Check Post",
        department="Rajkot Traffic Police",
        zone="Zone-5-Rajkot",
        camera_type="ptz",
        latitude=22.3039,
        longitude=70.8022,
        source_protocol=SourceProtocol.rtsp,
        # A non-routable TEST-NET address (RFC 5737): demonstrates that the
        # RTSP adapter path is fully wired end-to-end, without depending on
        # a physical camera being reachable from this environment.
        stream_ref="rtsp://198.51.100.42:554/stream1",
        storage_tier=StorageTier.warm,
        retention_days=30,
    ),
]

WATCHLIST = [
    dict(
        category=WatchlistCategory.stolen_vehicle,
        identifier_type=IdentifierType.plate,
        identifier_value="GJ01AB1234",
        label="Stolen vehicle - Maruti Swift (white)",
        description="Reported stolen from Ahmedabad on 2026-08-30. FIR GJ/AMD/2026/4521.",
        risk_level=AlertSeverity.high,
    ),
    dict(
        category=WatchlistCategory.blacklisted_vehicle,
        identifier_type=IdentifierType.plate,
        identifier_value="GJ05CD5678",
        label="Blacklisted - repeat toll evasion / suspended permit",
        description="Commercial permit suspended pending inquiry.",
        risk_level=AlertSeverity.critical,
    ),
    dict(
        category=WatchlistCategory.stolen_vehicle,
        identifier_type=IdentifierType.plate,
        identifier_value="DL08EF9012",
        label="Stolen vehicle - Royal Enfield motorcycle",
        description="Reported stolen from Delhi, interstate alert issued.",
        risk_level=AlertSeverity.high,
    ),
    dict(
        category=WatchlistCategory.blacklisted_vehicle,
        identifier_type=IdentifierType.plate,
        identifier_value="RJ14GH3456",
        label="Blacklisted - overloaded freight, repeat offender",
        description="Multiple overloading violations at weighbridge checkpoints.",
        risk_level=AlertSeverity.medium,
    ),
    dict(
        category=WatchlistCategory.wanted_person,
        identifier_type=IdentifierType.name,
        identifier_value="UNKNOWN-SUBJECT-014",
        label="Wanted person - outstanding non-bailable warrant",
        description="Synthetic record for demonstration of person-watchlist categories.",
        risk_level=AlertSeverity.critical,
    ),
    dict(
        category=WatchlistCategory.missing_person,
        identifier_type=IdentifierType.name,
        identifier_value="MISSING-CASE-2026-0091",
        label="Missing person - last seen near Surat bus stand",
        description="Synthetic record for demonstration of person-watchlist categories.",
        risk_level=AlertSeverity.medium,
    ),
]


def _ensure_users(db) -> User:
    admin = db.query(User).filter(User.username == "admin").first()
    if admin is None:
        admin = User(
            username="admin",
            email="admin@okdriver.local",
            full_name="Platform Administrator",
            hashed_password=hash_password("Admin@12345"),
            role=UserRole.admin,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
    if not db.query(User).filter(User.username == "operator").first():
        db.add(
            User(
                username="operator",
                email="operator@okdriver.local",
                full_name="Duty Operator",
                hashed_password=hash_password("Operator@12345"),
                role=UserRole.operator,
            )
        )
        db.commit()
    return admin


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin = _ensure_users(db)

        for cam in CAMERAS:
            if db.query(Camera).filter(Camera.id == cam["id"]).first():
                continue
            stream_ref = cam.pop("stream_ref")
            db.add(
                Camera(
                    **cam,
                    stream_ref_encrypted=encrypt_secret(stream_ref),
                    status=CameraStatus.offline,
                    onboarded_via="manual",
                    created_by=admin.id if admin else None,
                )
            )

        for entry in WATCHLIST:
            exists = (
                db.query(WatchlistEntry)
                .filter(WatchlistEntry.identifier_value == entry["identifier_value"])
                .first()
            )
            if exists:
                continue
            db.add(WatchlistEntry(**entry, created_by=admin.id if admin else None))

        db.commit()
        print(f"Seeded {len(CAMERAS)} cameras and {len(WATCHLIST)} watchlist entries (skipping any that already existed).")
    finally:
        db.close()


if __name__ == "__main__":
    run()
