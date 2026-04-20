from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class MessageResponse(BaseModel):
    message: str


class CreateFieldRequest(BaseModel):
    name: str
    description: str


class CreateFieldResponse(BaseModel):
    id: UUID


class FieldResponse(BaseModel):
    id: UUID
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    is_deleted: bool


class CreateProjectRequest(BaseModel):
    field_id: UUID
    name: str
    description: str
    is_private: bool


class CreateProjectResponse(BaseModel):
    id: UUID


class ProjectResponse(BaseModel):
    id: UUID
    field_id: UUID
    name: str
    description: str
    is_private: bool
    created_at: datetime
    updated_at: datetime


class ListFilesByProjectAndPathResponse(BaseModel):
    file_version_id: int | None = None
    name: str
    file_format: str
    updated_at: datetime | None = None
    type: str


class GetFilesAtCommitResponse(BaseModel):
    file_version_id: int
    name: str
    file_format: str
    updated_at: datetime | None = None


class FileVersionHistoryResponse(BaseModel):
    file_version_id: int
    version: int
    commit_id: int
    file_size: int
    is_deleted: bool
    created_at: datetime


class CommitVersionResponse(BaseModel):
    id: int
    message: str
    user_id: UUID
    is_complete: bool
    created_at: datetime


class UpdatePayload(BaseModel):
    values: dict[str, object]

