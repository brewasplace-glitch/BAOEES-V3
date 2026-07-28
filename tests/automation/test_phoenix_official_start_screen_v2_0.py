from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
html=ROOT/"phoenix/local_app/static/official_start_v2_0/index.html"
assert html.is_file()
text=html.read_text(encoding="utf-8")
for marker in ["127.0.0.1:8765","filePicker","Project Phoenix 2.0"]: assert marker in text
assert json.loads((ROOT/"configs/phoenix/official_start_screen_v2_0.json").read_text(encoding="utf-8"))["official"] is True
print("OFFICIAL START SCREEN TESTS PASSED")
