"""Start the v1 Streamlit app.

Windows Application Control blocks grpc's cygrpc DLL, which Chroma imports
only for telemetry. The stub lets the local chroma_db open without that DLL.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import _v1_grpc_stub

_v1_grpc_stub.install()

APP = ROOT / "src" / "app.py"
port = sys.argv[1] if len(sys.argv) > 1 else "8501"
sys.argv = [
    "streamlit",
    "run",
    str(APP),
    "--server.port",
    port,
    "--server.headless",
    "true",
    "--browser.gatherUsageStats",
    "false",
]

from streamlit.web import cli

raise SystemExit(cli.main())
