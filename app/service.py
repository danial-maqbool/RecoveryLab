"""Inspection history and copy-only recovery API."""

from __future__ import annotations
import json
import uuid
from pathlib import Path
from localdesk.base import BaseApplication
from localdesk.jobs import utcnow
from localdesk.safety import (
    InputError,
    checked_path,
    clean_name,
    digest,
    integer,
    unique_write,
)
from .formats import hex_view, inspect, repair


class Application(BaseApplication):
    def setup(self):
        self.store.execute(
            "CREATE TABLE IF NOT EXISTS inspections("
            "id TEXT PRIMARY KEY,path TEXT,created TEXT,report TEXT,output TEXT)"
        )

    def state(self):
        rows = self.store.rows(
            "SELECT id,path,created,report,output FROM inspections ORDER BY created DESC,rowid DESC LIMIT 100"
        )
        entries = []
        for row in rows:
            report = json.loads(row.pop("report"))
            row.update(
                {
                    k: report[k]
                    for k in [
                        "name",
                        "size",
                        "status",
                        "detected",
                        "repair_available",
                        "repair_label",
                    ]
                }
            )
            row["output"] = json.loads(row["output"]) if row["output"] else None
            entries.append(row)
        return {
            "entries": entries,
            "jobs": self.jobs.recent(),
            "stats": {
                "inspected": len(entries),
                "repairable": sum(e["repair_available"] for e in entries),
                "copies": sum(bool(e["output"]) for e in entries),
            },
        }

    def inspection(self, ident):
        row = self.store.one("SELECT * FROM inspections WHERE id=?", (str(ident),))
        if not row:
            raise InputError("This inspection does not exist.")
        row["report"] = json.loads(row["report"])
        row["output"] = json.loads(row["output"]) if row["output"] else None
        return row

    def get(self, action, query):
        if action == "inspection":
            return self.inspection(query.get("id", ""))
        if action == "hex":
            row = self.inspection(query.get("id", ""))
            path = checked_path(row["path"])
            return {
                "rows": hex_view(
                    path.read_bytes(), integer(query.get("offset", 0), 0, 25 * 1024**2)
                ),
                "size": path.stat().st_size,
            }
        if action == "examples":
            return {
                "files": [
                    str(p)
                    for p in sorted((self.root / "examples").iterdir())
                    if p.is_file() and p.name != "README.txt"
                ]
            }
        return super().get(action, query)

    def post(self, action, body):
        if action == "inspect":
            paths = body.get("paths") or [body.get("path", "")]
            if not isinstance(paths, list) or not 1 <= len(paths) <= 20:
                raise InputError("Inspect between 1 and 20 files per batch.")
            sources = [checked_path(p) for p in paths]

            def work(context):
                results = []
                for index, path in enumerate(sources):
                    context.progress(
                        int(index / len(sources) * 100), f"Inspecting {path.name}"
                    )
                    report = inspect(path.read_bytes(), path.name)
                    ident = uuid.uuid4().hex
                    self.store.execute(
                        "INSERT INTO inspections VALUES(?,?,?,?,NULL)",
                        (ident, str(path), utcnow(), json.dumps(report)),
                    )
                    results.append({"id": ident, "report": report})
                return {"inspections": results}

            return {"job_id": self.jobs.submit("Inspect files", work)}
        if action == "repair":
            row = self.inspection(body.get("id", ""))
            source = checked_path(row["path"])

            def work(context):
                context.progress(10, "Checking the source hash.")
                if digest(source) != row["report"]["sha256"]:
                    raise InputError(
                        "The source changed after inspection. Inspect it again."
                    )
                context.progress(25, "Creating a new recovered copy.")
                content, extension, notes = repair(
                    source.read_bytes(),
                    source.name,
                    escape_formulas=bool(body.get("escape_formulas", True)),
                )
                output = self.new_output("recovered")
                path = unique_write(
                    output / clean_name(source.stem + ".recovered" + extension), content
                )
                after = inspect(content, path.name)
                original_unchanged = digest(source) == row["report"]["sha256"]
                record = {
                    "original_sha256": row["report"]["sha256"],
                    "output_sha256": after["sha256"],
                    "original_unchanged": original_unchanged,
                    "notes": notes,
                    "before_status": row["report"]["status"],
                    "after_status": after["status"],
                    "output": self.artifact(path),
                }
                report_path = unique_write(
                    output / "recovery-report.json",
                    json.dumps(record, indent=2).encode("utf-8"),
                )
                record["report"] = self.artifact(report_path)
                self.store.execute(
                    "UPDATE inspections SET output=? WHERE id=?",
                    (json.dumps(record), row["id"]),
                )
                context.progress(100, "Recovered copy and report are ready.")
                return record

            return {"job_id": self.jobs.submit("Recover file copy", work)}
        if action == "export":
            row = self.inspection(body.get("id", ""))
            folder = self.new_output("inspection-report")
            output = unique_write(
                folder / "inspection.json",
                json.dumps(row["report"], indent=2).encode("utf-8"),
            )
            return self.artifact(output)
        return super().post(action, body)
