from sqlalchemy import select
from sqlalchemy.orm import Session

from creator_studio.domain.camera.models import (
    CameraAnchor,
    CameraQCReport,
    CameraRig,
    ShotCameraBinding,
)
from creator_studio.infrastructure.db.models.camera import (
    CameraAnchorRow,
    CameraQCReportRow,
    CameraRigRow,
    ShotCameraBindingRow,
)
from creator_studio.infrastructure.db.repositories import mappers


class SqlAlchemyCameraRigRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, value: CameraRig) -> CameraRig:
        self._session.add(mappers.camera_rig_to_row(value))
        return value

    def save(self, value: CameraRig) -> CameraRig:
        self._session.merge(mappers.camera_rig_to_row(value))
        return value

    def get(self, id: str) -> CameraRig | None:
        row = self._session.get(CameraRigRow, str(id))
        return mappers.camera_rig_from_row(row) if row else None

    def list_for_project(self, id: str) -> list[CameraRig]:
        rows = self._session.scalars(
            select(CameraRigRow).where(CameraRigRow.project_id == str(id))
        ).all()
        return [mappers.camera_rig_from_row(row) for row in rows]


class SqlAlchemyCameraAnchorRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, value: CameraAnchor) -> CameraAnchor:
        self._session.add(mappers.camera_anchor_to_row(value))
        return value

    def save(self, value: CameraAnchor) -> CameraAnchor:
        self._session.merge(mappers.camera_anchor_to_row(value))
        return value

    def get(self, id: str) -> CameraAnchor | None:
        row = self._session.get(CameraAnchorRow, str(id))
        return mappers.camera_anchor_from_row(row) if row else None

    def list_for_rig(self, id: str) -> list[CameraAnchor]:
        rows = self._session.scalars(
            select(CameraAnchorRow).where(CameraAnchorRow.rig_id == str(id))
        ).all()
        return [mappers.camera_anchor_from_row(row) for row in rows]


class SqlAlchemyShotCameraBindingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, value: ShotCameraBinding) -> ShotCameraBinding:
        self._session.add(mappers.shot_camera_binding_to_row(value))
        return value

    def save(self, value: ShotCameraBinding) -> ShotCameraBinding:
        self._session.merge(mappers.shot_camera_binding_to_row(value))
        return value

    def get(self, id: str) -> ShotCameraBinding | None:
        row = self._session.get(ShotCameraBindingRow, str(id))
        return mappers.shot_camera_binding_from_row(row) if row else None

    def list_for_shot(self, id: str) -> list[ShotCameraBinding]:
        rows = self._session.scalars(
            select(ShotCameraBindingRow).where(ShotCameraBindingRow.shot_id == str(id))
        ).all()
        return [mappers.shot_camera_binding_from_row(row) for row in rows]


class SqlAlchemyCameraQCReportRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, value: CameraQCReport) -> CameraQCReport:
        self._session.add(mappers.camera_qc_report_to_row(value))
        return value

    def save(self, value: CameraQCReport) -> CameraQCReport:
        self._session.merge(mappers.camera_qc_report_to_row(value))
        return value

    def get(self, id: str) -> CameraQCReport | None:
        row = self._session.get(CameraQCReportRow, str(id))
        return mappers.camera_qc_report_from_row(row) if row else None

    def list_for_attempt(self, id: str) -> list[CameraQCReport]:
        rows = self._session.scalars(
            select(CameraQCReportRow).where(CameraQCReportRow.attempt_id == str(id))
        ).all()
        return [mappers.camera_qc_report_from_row(row) for row in rows]
