"""Initialize fresh deployments; refuse silently upgrading incompatible schemas."""

from sqlalchemy import inspect
from sqlmodel import SQLModel, Session
from app.core.db import engine, init_db
import app.models  # register every table


def main():
    inspector = inspect(engine)
    for name, table in SQLModel.metadata.tables.items():
        if inspector.has_table(name):
            missing = set(table.columns.keys()) - {
                c["name"] for c in inspector.get_columns(name)
            }
            if missing:
                raise RuntimeError(
                    f"Existing table {name} needs a reviewed migration: {sorted(missing)}"
                )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        init_db(session)


if __name__ == "__main__":
    main()
