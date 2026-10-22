# Bắt đầu với RescueLink v0.2

Đề tài: **Xây dựng và đánh giá hệ thống hỗ trợ cứu hộ thiên tai sử dụng mạng P2P/DTN và AI phân loại yêu cầu khẩn cấp**.

Bản này hoàn thiện mã nguồn MVP nghiên cứu theo phạm vi trong README. Không gọi là hệ thống cứu hộ thực tế đã nghiệm thu. `docs/VERIFICATION.md` phân biệt kết quả tự động và phần cần điện thoại.

## 1. Mở mã nguồn trên Windows

1. Giải nén ZIP vào `C:\RescueLink_v0.2`. Bên trong có thư mục `rescue-link`.
2. Mở **VS Code → File → Open Folder → C:\RescueLink_v0.2\rescue-link**.
3. Mở **Terminal → New Terminal**, chọn **PowerShell**.
4. Giữ nguyên bộ v0.1 để đối chiếu; bản ZIP không chứa mật khẩu `.env` của bạn.

Không cần Docker trên Windows nếu backend vẫn chạy trong Ubuntu VM.

## 2. Cập nhật server ở Ubuntu VM

Chép thư mục mới qua VMware shared folder/USB. Mở **Terminal của Ubuntu**. Giả sử bản mới ở `~/Downloads/RescueLink_v0.2/rescue-link`:

```bash
cd ~/rescue-link
cp -a backend ../backend-v0.1-backup
cp -a dashboard ../dashboard-v0.1-backup
cp -a scripts ../scripts-v0.1-backup
cp -a ~/Downloads/RescueLink_v0.2/rescue-link/backend .
cp -a ~/Downloads/RescueLink_v0.2/rescue-link/dashboard .
cp -a ~/Downloads/RescueLink_v0.2/rescue-link/scripts .
cp -a ~/Downloads/RescueLink_v0.2/rescue-link/ai .
cp -a ~/Downloads/RescueLink_v0.2/rescue-link/simulation .
cp -a ~/Downloads/RescueLink_v0.2/rescue-link/docs .
cp ~/Downloads/RescueLink_v0.2/rescue-link/README.md .
sudo docker compose up -d --build
sudo docker compose ps
curl http://localhost:8080/api/health
```

Kỳ vọng: `version: 0.2.0`, `mode: DRILL_ONLY`. Giữ nguyên `.env`, `compose.yaml` và volume DB đang dùng; không chạy `down -v`. Schema không thay đổi nên các SOS cũ vẫn giữ; trường AI lưu trên SOS cũ vẫn là kết quả baseline cũ. Tin mới dùng model mới.

Nếu cài server lần đầu: `python3 scripts/setup.py` rồi `sudo docker compose up -d --build`. Model đã kèm ZIP; Docker không phải huấn luyện lại.

## 3. Mở Dashboard

**Chrome/Edge trên Windows**: mở `http://IP_WINDOWS:8080` khi portproxy cũ còn đúng, hoặc `http://IP_VM:8080` từ Windows. Các IP bạn từng dùng: Windows `172.16.0.69`, VM `192.168.43.128`; kiểm tra lại trước mỗi buổi test. Không dùng `172.17.0.1`/`172.18.0.1` trên Redmi: đó là mạng Docker.

Lấy ADMIN_TOKEN trong `.env` Ubuntu, nhập vào web. Nhấn Ctrl+F5 khi cập nhật. Dùng khu vực **Thử phân loại nội dung**, nhập nội dung giả lập và bấm **Phân loại thử**. Model trả điểm chưa hiệu chỉnh xác suất; người điều phối quyết định cuối cùng.

Thử: chọn SOS → xác minh → nhập tên đội → phân công → hoàn tất. Điều chỉnh mức điều phối cần lý do, không sửa nội dung có chữ ký. Heatmap dùng dữ liệu trang đang xem và chỉ SOS chưa hoàn tất; không suy ra số dân chịu thiên tai từ bản đồ này.

## 4. Chạy Android trên Redmi

**PowerShell trong VS Code**, tại thư mục mới:

```powershell
cd C:\RescueLink_v0.2\rescue-link
flutter --version
flutter doctor -v
python scripts\bootstrap_mobile.py
cd mobile
flutter pub get
flutter analyze
flutter devices
flutter run -d MA_THIET_BI
```

`MA_THIET_BI` lấy cột ID trong `flutter devices`, không mặc định dùng tên model. Chọn Android device, không chọn Windows/Web.

Bootstrap dành cho thư mục mới chưa có `mobile/android`. Nếu cập nhật ngay trong project đã có Android: sao chép mã nguồn mới rồi chạy `python scripts\update_mobile.py` tại thư mục gốc. Script sao lưu Android app trước, giữ Gradle wrapper/settings/NDK của bạn và chép Kotlin/manifest mới.

AGP 9 cần Flutter >=3.47 để dùng built-in Kotlin. Script đọc AGP: AGP 9 bật `android.builtInKotlin=true` và bỏ KGP ở app; AGP 8 giữ KGP >=2.0. Giữ `android.newDsl` theo template Flutter; file app tạm suppress deprecation legacy DSL. Chưa build Android v0.2 trong môi trường tạo ZIP.

Lỗi `Package ndk not found`: **Android Studio → More Actions/Settings → SDK Manager → SDK Tools → Show Package Details → NDK (Side by side)**, chọn đúng version `flutter.ndkVersion` báo trong lỗi (máy bạn từng yêu cầu `28.2.13676358`), Apply. Không đổi NDK tùy tiện để che lỗi.

Redmi: bật USB debugging, chấp nhận RSA; bật Bluetooth, Wi-Fi, Vị trí, cấp quyền Nearby. Khi đo chạy nền, ghi lại cài đặt pin của app; không giả định mọi Redmi đều giữ service sống. Chi tiết: `ANDROID.md`.

## 5. Gửi SOS từ Redmi lên server

1. Trong Chrome Redmi, mở `http://IP_WINDOWS:8080/api/health` qua portproxy. Phải thấy JSON; nếu không, xử lý LAN/VM trước.
2. App → **Tiếp sức**: URL gốc `http://IP_WINDOWS:8080`, DRILL_KEY từ `.env`. Không thêm `/api`; không dùng ADMIN_TOKEN ở app.
3. **Lưu cấu hình**, sang **Tạo SOS**, nhập nội dung và địa điểm diễn tập, lưu.
4. **Đồng bộ ngay**. Kiểm tra hộp tin “Server đã nhận” và Dashboard có cùng message ID. “Một relay đã lưu” là mức xác nhận khác.
5. App debug cho phép HTTP LAN. Bản release cần HTTPS; dùng `flutter build apk --debug` nếu muốn APK diễn tập LAN và cài file `mobile/build/app/outputs/flutter-apk/app-debug.apk`.

Nếu lỗi: đọc lỗi từng tin; 401: sai DRILL_KEY; 410: hết TTL; 422: chữ ký/schema/đồng hồ; 429: quota hoặc nginx; không kết nối: kiểm tra URL, firewall, portproxy và IP mới.

## 6. Kiểm thử offline và đo

Cài app lên ít nhất 3 Android. Làm đúng `FIELD_TEST.md`: A gặp B, sau đó A rời đi, B gặp C, C lên mạng. Không để A và C gặp nhau trong phép thử hai hop. Tắt dữ liệu di động và Wi-Fi có Internet ở giai đoạn offline; vẫn bật Bluetooth/Wi-Fi để Nearby hoạt động.

**Tiếp sức → Sao chép nhật ký đo** trên từng máy; dán vào `A.jsonl`, `B.jsonl`, `C.jsonl` trên máy tính:

```powershell
python scripts\evaluate_logs.py A.jsonl B.jsonl C.jsonl --out field-evaluation.json
```

Phải thu log nguồn A để xác định mẫu số. Đồng bộ giờ trước test. Log tối đa khoảng 512 KB rồi giữ 1.000 dòng gần nhất; xuất sau mỗi lần thử. Bằng chứng pin dùng phép đo riêng, không suy ra từ simulator.

## 7. Tái lập AI và simulator

**Ubuntu Terminal hoặc PowerShell**, tại gốc dự án, dùng Python 3.12:

```bash
python -m venv .venv
```

Ubuntu: `source .venv/bin/activate`. PowerShell: `.venv\Scripts\Activate.ps1` (nếu activation bị policy chặn, gọi `.venv\Scripts\python.exe` trực tiếp).

```bash
python -m pip install -r backend/requirements.txt -r ai/requirements.txt
python ai/train.py
python simulation/dtn.py --nodes 30 --seeds 10 --out simulation/results/repeated30
python simulation/dtn.py --nodes 100 --seeds 10 --out simulation/results/repeated100
```

Huấn luyện lại với dữ liệu mới cần group_id đúng, duyệt nhãn; sau đó chép `ai/artifacts/triage_model.json` vào `backend/models/triage_model.json`, rebuild API. Xem `ai/README.md`. Đánh giá mẫu: `EVALUATION.md`.
