"""Create three signed DRILL events. Upload only to the URL supplied by the user."""
from pathlib import Path
import argparse
import base64
import hashlib
import json
import os
import time
import uuid
import urllib.request
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://localhost:8080")
parser.add_argument("--output", help="Write packets to JSON instead of uploading")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
settings = {}
if (root / ".env").exists():
    for line in (root / ".env").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=",1); settings[key] = value
gateway_key = os.getenv("DRILL_KEY", settings.get("DRILL_KEY", ""))
if not args.output and len(gateway_key)<24:
    raise SystemExit("Chạy scripts/setup.py trước hoặc đặt biến DRILL_KEY.")
signing_key = ec.generate_private_key(ec.SECP256R1())
public_der = signing_key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
b64 = lambda value: base64.b64encode(value).decode()
examples = [
    (1, "Điểm diễn tập Sơn Trà", "DIỄN TẬP: một người cần hỗ trợ y tế, nhóm đang chờ tại điểm hẹn.",16.091,108.252,["medical"],2),
    (2, "Điểm diễn tập Hòa Vang", "DIỄN TẬP: ba người cần hỗ trợ sơ tán.",16.017,108.130,["evacuation"],3),
    (3, "Điểm diễn tập Hải Châu", "DIỄN TẬP: cần bổ sung nước uống cho nhóm.",16.065,108.214,["water"],5),
]
packets = []
for priority, place, text, lat, lon, needs, people in examples:
    now=int(time.time()*1000)
    body=dict(protocol_version=1, incident_id=str(uuid.uuid4()), origin_key_id=hashlib.sha256(public_der).hexdigest(),created_at_ms=now,expires_at_ms=now+86400000,priority=priority,hop_limit=8,text=text,location_text=place,latitude=lat,longitude=lon,accuracy_m=30.0,location_captured_at_ms=now,people_count=people,needs=needs,is_drill=True)
    raw=json.dumps(body,ensure_ascii=False,separators=(",",":")).encode()
    envelope=dict(message_id=hashlib.sha256(raw).hexdigest(),body_b64=b64(raw),public_key_b64=b64(public_der),signature_b64=b64(signing_key.sign(b"RescueLink/v1:"+raw,ec.ECDSA(hashes.SHA256()))),hop_count=0)
    packets.append(envelope)
    if not args.output:
        request=urllib.request.Request(args.url.rstrip('/')+"/api/v1/sos",data=json.dumps(envelope).encode(),headers={"Content-Type":"application/json","X-Drill-Key":gateway_key},method="POST")
        with urllib.request.urlopen(request,timeout=10) as response:
            print(place, response.status, json.load(response)["status"])
if args.output:
    Path(args.output).write_text(json.dumps(packets,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Đã ghi {len(packets)} gói diễn tập vào {args.output}")
