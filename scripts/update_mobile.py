"""Update an existing generated Android app, with a backup first."""
from datetime import datetime,timezone
from pathlib import Path
import shutil
from mobile_config import configure
root=Path(__file__).resolve().parents[1]
android=root/'mobile/android'
if not android.exists():raise SystemExit('Chạy python scripts/bootstrap_mobile.py cho lần đầu.')
# Validate before any changes.
if not (android/'settings.gradle.kts').exists():raise SystemExit('Chỉ hỗ trợ Kotlin DSL; chưa sửa file nào.')
backup=root/'mobile/backups'/datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
backup.mkdir(parents=True)
shutil.copytree(android/'app',backup/'app',ignore=shutil.ignore_patterns('build'))
shutil.copy2(android/'gradle.properties',backup/'gradle.properties')
shutil.copytree(root/'mobile/android-overrides',android,dirs_exist_ok=True)
configure(android)
print(f'Đã cập nhật; bản sao Android cũ: {backup}')
print('Tiếp theo: cd mobile; flutter pub get; flutter analyze; flutter run')
