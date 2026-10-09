"""Parse documents in a disposable process with a hard execution deadline."""
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from app.core.parsers import CharLocation, ParsedDocument, ParserError, parse_file


def parse_bounded(path: Path, filename: str, timeout: int = 60) -> ParsedDocument:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "app.core.parse_worker", str(path.resolve()), filename],
            capture_output=True, text=True, encoding="utf-8", timeout=timeout,
            cwd=Path(__file__).resolve().parents[2],
        )
    except subprocess.TimeoutExpired as exc:
        raise ParserError("Document parsing exceeded the time limit. Use a smaller or simpler document.") from exc
    if result.returncode:
        raise ParserError("Document could not be parsed. Use a valid, readable, unlocked file.")
    try:
        data = json.loads(result.stdout)
        data["locations"] = [CharLocation(**item) for item in data["locations"]]
        return ParsedDocument(**data)
    except (ValueError, TypeError, KeyError) as exc:
        raise ParserError("The parser returned invalid document data.") from exc


if __name__ == "__main__":
    print(json.dumps(asdict(parse_file(sys.argv[1], filename=sys.argv[2])), ensure_ascii=False))
