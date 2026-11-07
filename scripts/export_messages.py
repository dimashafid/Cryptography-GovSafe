"""Export/dekripsi pesan melalui CLI admin; jangan jalankan di mesin bersama."""
import argparse
import json
from pathlib import Path
from services.message_service import export_all_messages

parser = argparse.ArgumentParser(description="Export Undergrid encrypted messages")
parser.add_argument("--output", default="messages_export.json")
args = parser.parse_args()
rows = export_all_messages()
output = Path(args.output)
output.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
try:
    output.chmod(0o600)
except OSError:
    pass
print(f"{len(rows)} pesan diekspor. Lindungi file hasil karena berisi plaintext.")
