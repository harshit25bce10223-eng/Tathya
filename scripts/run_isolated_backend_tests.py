"""Run tests in a disposable PostgreSQL database; never reuse application data."""
import os
import pathlib
import subprocess
import sys
import uuid

import psycopg
from psycopg import sql

ROOT = pathlib.Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "backend"))
from app.core.config import settings

name = "tathya_audit_test_" + uuid.uuid4().hex[:12]
base = str(settings.DATABASE_URL).replace("postgresql+psycopg://", "postgresql://")
connection = psycopg.connect(base, autocommit=True, connect_timeout=5)
connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
output = ROOT / "artifacts/system-repair-validation"
output.mkdir(parents=True, exist_ok=True)
runtime = output / name
runtime.mkdir()
env = os.environ.copy()
env.update(DATABASE_URL=base.rsplit("/", 1)[0] + "/" + name,
           STORAGE_DIR=str(runtime / "storage"),
           ECDSA_PRIVATE_KEY_PATH=str(runtime / "private.pem"),
           ECDSA_PUBLIC_KEY_PATH=str(runtime / "public.pem"),
           LLM_CACHE_DIR=str(runtime / "cache"), HF_HUB_OFFLINE="1")
try:
    subprocess.run([sys.executable, "-c", "from sqlmodel import SQLModel; from app.core.db import engine; import app.models; SQLModel.metadata.create_all(engine)"], env=env, check=True)
    with (output / "backend-tests.log").open("w", encoding="utf-8") as log:
        result = subprocess.run([sys.executable, "-m", "pytest", "backend/tests", "-q", "-ra", "--tb=short"], env=env, stdout=log, stderr=subprocess.STDOUT)
    print((output / "backend-tests.log").read_text(encoding="utf-8")[-14000:])
finally:
    connection.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
    connection.close()
sys.exit(result.returncode)
