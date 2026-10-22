"""Generate official Flutter Android scaffolding, then install project overrides."""
from pathlib import Path
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
mobile = root / "mobile"
flutter = shutil.which("flutter")
if not flutter:
    sys.exit("Chưa có Flutter trong PATH. Cài Flutter và chạy flutter doctor trước.")
if (mobile / "android").exists():
    sys.exit("mobile/android đã tồn tại. Không ghi đè code đã sửa. Đọc docs/ANDROID.md để cập nhật thủ công.")
preserved = {path: path.read_bytes() for path in [mobile / "pubspec.yaml", mobile / "lib" / "main.dart", mobile / "analysis_options.yaml"]}
try:
    subprocess.run([flutter, "create", "--platforms=android", "--org", "vn.edu.rescuelink", "--project-name", "rescue_link", "--no-pub", "."], cwd=mobile, check=True)
finally:
    for path, content in preserved.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
# flutter create may add its starter test; it does not describe this app.
starter = mobile / "test" / "widget_test.dart"
if starter.exists():
    starter.unlink()
shutil.copytree(mobile / "android-overrides", mobile / "android", dirs_exist_ok=True)
from mobile_config import configure
configure(mobile / "android")
subprocess.run([flutter, "pub", "get"], cwd=mobile, check=True)
print("Đã tạo Android project. Tiếp theo: cd mobile && flutter analyze && flutter run")
