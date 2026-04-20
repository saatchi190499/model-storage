import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Field(Base):
    __tablename__ = "fields"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    field_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("fields.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    is_private: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)


class Commit(Base):
    __tablename__ = "commits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_commit_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("commits.id"), nullable=True)
    is_complete: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)


class File(Base):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    last_file_version_id: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    file_format: Mapped[str] = mapped_column(String(20), server_default=text("'.txt'"), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)


class FileVersion(Base):
    __tablename__ = "file_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_id: Mapped[int] = mapped_column(Integer, ForeignKey("files.id"), nullable=False)
    storage_key: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    hash: Mapped[str] = mapped_column(Text, nullable=False)
    commit_id: Mapped[int] = mapped_column(Integer, ForeignKey("commits.id"), nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)


