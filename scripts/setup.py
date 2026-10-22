"""Create local credentials without overwriting an existing environment."""
from pathlib import Path
import secrets

root = Path(__file__).resolve().parents[1]
path = root / ".env"
if path.exists():
    print(".env đã tồn tại; giữ nguyên. Không tạo lại mật khẩu DB đang dùng.")
else:
    path.write_text("\n".join([
        f"POSTGRES_PASSWORD={secrets.token_hex(24)}",
        f"ADMIN_TOKEN={secrets.token_hex(24)}",
        f"DRILL_KEY={secrets.token_hex(24)}",
        "DASHBOARD_PORT=8080", "",
    ]), encoding="utf-8")
    path.chmod(0o600)
    print("Đã tạo .env. ADMIN_TOKEN dùng đăng nhập web; DRILL_KEY chỉ nhập trên gateway.")
    print("Tiếp theo: docker compose up -d --build")
