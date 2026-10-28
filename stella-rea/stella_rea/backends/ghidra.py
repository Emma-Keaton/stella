"""Ghidra backend: native static analysis, headless.

Ghidra ships ``analyzeHeadless``, which runs the full Ghidra analyser over a
binary in a temporary project and can export results without a GUI.  This
adapter is a real, working integration: it drives ``analyzeHeadless`` with a
small Jython export script and parses the JSON it writes.

Honesty rules:
* a missing ``analyzeHeadless`` binary raises
  :class:`stella_rea.errors.BackendUnavailable`;
* a non-zero exit raises :class:`stella_rea.errors.ExecutionFailed`;
* unparseable export output yields an evidence bundle whose records are
  explicitly marked as *no evidence* at low confidence.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..evidence import Confidence, Evidence, EvidenceBundle, Provenance, SourceKind
from ..errors import ExecutionFailed
from . import Backend, CommandResult

__all__ = ["GhidraBackend"]

#: The Jython export script handed to Ghidra's script manager.  It walks the
#: program listing and writes a JSON description of what it found.
EXPORT_SCRIPT = """#@category stella-rea
import json

args = getScriptArgs()
out_path = args[0]
currentProgram = getCurrentProgram()
listing = currentProgram.getListing()

functions = []
for func in listing.getFunctions(True):
    functions.append({
        "name": func.getName(),
        "entry": func.getEntryPoint().toString(),
        "size": int(func.getBody().getNumAddresses()),
    })

data = {
    "program": currentProgram.getName(),
    "language": currentProgram.getLanguageID().toString(),
    "functions": functions,
}
with open(out_path, "w") as handle:
    json.dump(data, handle)
"""


class GhidraBackend(Backend):
    """Native static analysis via Ghidra's headless analyser."""

    name = "ghidra"
    binary = "analyzeHeadless"
    kind = "static"
    available = True
    limitation = ""

    def build_argv(
        self,
        target: str | Path,
        project: str | Path,
        project_name: str,
        script: str | Path,
        output: str | Path,
    ) -> list[str]:
        """Build the ``analyzeHeadless`` command line.

        The layout is ``analyzeHeadless <project_dir> <project_name> -import
        <target> -scriptPath <dir> -postScript <script> <out.json>``.
        """
        return [
            self.binary,
            str(project),
            project_name,
            "-import",
            str(target),
            "-scriptPath",
            str(Path(script).parent),
            "-postScript",
            Path(script).name,
            str(output),
        ]

    def analyze(
        self,
        target: str | Path,
        project: str | Path,
        project_name: str = "stella_rea",
        script: str | Path | None = None,
        output: str | Path | None = None,
        timeout: int = 1800,
    ) -> CommandResult:
        """Run the headless analyser over ``target``.

        Raises:
            BackendUnavailable: when ``analyzeHeadless`` is not installed.
            ExecutionFailed: when the command fails or cannot be started.
        """
        self.require()
        project_dir = Path(project)
        project_dir.mkdir(parents=True, exist_ok=True)
        script_path = Path(script) if script else project_dir / "stella_export.py"
        if not script_path.exists():
            script_path.write_text(EXPORT_SCRIPT, encoding="utf-8")
        out_path = Path(output) if output else project_dir / "stella_export.json"
        argv = self.build_argv(target, project_dir, project_name, script_path, out_path)
        result = self.run(argv, timeout=timeout)
        if not result.ok:
            raise ExecutionFailed(
                f"ghidra headless analysis failed with exit code {result.returncode}",
                argv=list(argv),
                returncode=result.returncode,
                stderr=result.stderr[-4000:],
            )
        return result


    def parse_export(self, output: str | Path) -> dict[str, Any]:
        """Parse the JSON export Ghidra wrote.

        Returns an empty mapping when the file is missing or malformed; the
        caller turns that into an explicit *no evidence* record.
        """
        path = Path(output)
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except (json.JSONDecodeError, OSError):
            return {}
        return data if isinstance(data, dict) else {}

    def extract(
        self,
        target: str | Path,
        project: str | Path,
        project_name: str = "stella_rea",
        script: str | Path | None = None,
        output: str | Path | None = None,
        timeout: int = 1800,
    ) -> EvidenceBundle:
        """Analyse ``target`` and return an evidence bundle.

        Raises:
            BackendUnavailable: when ``analyzeHeadless`` is not installed.
            ExecutionFailed: when the analysis fails.
        """
        provenance = Provenance(("ghidra.analyzeHeadless",))
        bundle = EvidenceBundle(provenance=provenance, target=str(target))
        result = self.analyze(
            target,
            project,
            project_name=project_name,
            script=script,
            output=output,
            timeout=timeout,
        )
        bundle.provenance = provenance.add("ghidra.parse_export")
        out_path = Path(output) if output else Path(project) / "stella_export.json"
        data = self.parse_export(out_path)
        functions = data.get("functions") or []
        if not functions:
            bundle.add(
                Evidence(
                    claim="ghidra export contained no functions; nothing was observed",
                    source=SourceKind.GHIDRA,
                    confidence=Confidence.NONE,
                    provenance=bundle.provenance,
                    found=False,
                    detail={"returncode": result.returncode},
                    locator=str(out_path),
                )
            )
            return bundle
        names = [str(f.get("name", "")) for f in functions if isinstance(f, dict)]
        bundle.add(
            Evidence(
                claim=f"ghidra recovered {len(functions)} functions",
                source=SourceKind.GHIDRA,
                confidence=Confidence.HIGH,
                provenance=bundle.provenance,
                detail={"count": len(functions), "names": names[:500]},
                locator=str(out_path),
            )
        )
        bundle.add(
            Evidence(
                claim=f"analysed program {data.get('program', '?')}",
                source=SourceKind.GHIDRA,
                confidence=Confidence.HIGH,
                provenance=bundle.provenance,
                detail={"language": data.get("language", "")},
                locator=str(out_path),
            )
        )
        return bundle


