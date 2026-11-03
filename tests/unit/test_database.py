"""Unit tests for the database layer that need no running PostgreSQL."""

import os
import subprocess
import sys

from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    Table,
    UniqueConstraint,
)
from sqlalchemy.schema import CreateTable

from app.config import REPO_ROOT
from app.models.base import Base


def test_constraint_names_follow_the_convention() -> None:
    # A throwaway metadata copy, so no table is added to the real Base.
    metadata = type(Base.metadata)(naming_convention=Base.metadata.naming_convention)
    Table("parents", metadata, Column("id", Integer, primary_key=True))
    child = Table(
        "children",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("parent_id", Integer, ForeignKey("parents.id")),
        Column("position", Integer),
        UniqueConstraint("parent_id", "position"),
        CheckConstraint("position >= 0", name="position_not_negative"),
    )

    ddl = str(CreateTable(child))

    assert "CONSTRAINT pk_children PRIMARY KEY" in ddl
    assert "CONSTRAINT fk_children_parent_id_parents FOREIGN KEY" in ddl
    assert "CONSTRAINT uq_children_parent_id_position UNIQUE" in ddl
    assert "CONSTRAINT ck_children_position_not_negative CHECK" in ddl


def test_importing_the_app_does_not_create_an_engine() -> None:
    # A fresh interpreter, so other tests that use the engine cannot affect it.
    code = (
        "import app.main, app.database.session as s;"
        "print(s.get_engine.cache_info().currsize)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "backend")},
    )

    assert result.stdout.strip() == "0"
