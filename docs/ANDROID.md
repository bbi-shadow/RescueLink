# Chạy Flutter/Android

## Chuẩn bị

- Flutter SDK trong PATH, Android Studio + Android SDK; dùng JDK được Flutter/Android Studio hỗ trợ.
- Android 8.0 (API 26) trở lên có Google Play services. Target của PoC: API 35.
- Bật Developer options → USB debugging; kết nối USB và xác nhận trên điện thoại.
- Hai điện thoại trở lên; Android emulator không thay thế việc test radio trên máy thật.

```bash
flutter doctor -v
flutter doctor --android-licenses
flutter devices
```

Xem và chấp nhận giấy phép Android nếu đồng ý. `flutter doctor` cần báo Android toolchain sẵn sàng.

## Tạo phần Android

Tại thư mục gốc `rescue-link`:

```bash
python3 scripts/bootstrap_mobile.py
cd mobile
flutter analyze
flutter run -d MA_THIET_BI
```

Windows dùng `python scripts/bootstrap_mobile.py`. Đừng chạy app với target Windows/Web; MethodChannel của bản này chỉ có Android.

`flutter create` tạo project `vn.edu.rescuelink.rescue_link`. Bootstrap chép `android-overrides/app` vào `android/app`; các phần Gradle settings/root/wrapper theo template Flutter.

Nếu cần chép cập nhật sau khi đã tạo project, so sánh file rồi chép có chọn lọc. Không xóa thư mục Android đã sửa mà chưa có bản sao.

## Thử hai máy A–B

1. Cài cùng bản app trên cả hai máy.
2. Bật Bluetooth, Wi-Fi và dịch vụ Vị trí. Tắt mobile data; không kết nối Wi-Fi có Internet để chứng minh offline.
3. Mở tab **Tiếp sức** → **Cấp quyền** → **Bật tiếp sức**.
4. Hai máy hiện mã; chỉ chấp nhận nếu mã giống nhau. Nếu lỡ thời hạn, dừng/bật tiếp sức trên cả hai rồi thử lại.
5. A mở **Tạo SOS**, nhập mô tả diễn tập và địa điểm, lưu.
6. B mở **Hộp tin**, chờ chu kỳ inventory tối đa khoảng 15 giây cộng thời gian kết nối/truyền.
7. A hiển thị “Một relay đã lưu” khi nhận ACK. Đây không phải xác nhận trung tâm đã nhận.

Không cần Internet lúc tạo khóa, ký, lưu hoặc truyền P2P. App và Google Play services phải được cài/sẵn sàng trước khi đi offline.

## Thử ba máy A–B–C

1. A gặp B; B phải hiển thị SOS.
2. Cho A rời phạm vi hoặc tắt tiếp sức A sau khi B đã lưu.
3. Đóng/mở app B để chứng minh dữ liệu còn; bật tiếp sức lại.
4. B gặp C và xác nhận mã; C nhận SOS.
5. C có kết nối tới server và đã lưu URL + DRILL_KEY → bấm **Đồng bộ ngay**.
6. Dashboard hiện đúng một SOS; C hiển thị “Server đã nhận”. A/B vẫn có thể chưa biết server đã nhận vì v0.2 chưa gossip receipt.

## Địa chỉ server

- Backend chạy trong Docker trên laptop: điện thoại dùng `http://IP_LAPTOP:8080`.
- `localhost` trên điện thoại là chính điện thoại, không phải laptop.
- Nếu server ở Ubuntu VM: ưu tiên Bridged networking để điện thoại và VM cùng LAN. Kiểm tra `hostname -I` trong VM và mở URL `/api/health` trên trình duyệt điện thoại.
- Wi-Fi có AP/client isolation có thể chặn đường LAN; kiểm tra ở mạng thử nghiệm khác nếu cần.
- Nhập URL gốc, không thêm `/api` vì app tự thêm `/api/v1/sos`.
- DRILL_KEY lấy từ `.env` của server. Không nhập ADMIN_TOKEN vào gateway.
- Máy A/B không upload thì để trống cấu hình server.

`debug` cho phép HTTP trong LAN để test; manifest main mặc định chặn cleartext. Bản release cần máy chủ HTTPS hợp lệ. Đừng đưa app debug chứa dữ liệu nhạy cảm lên môi trường thực tế.

## Vị trí

App thử lấy vị trí trong 12 giây, có thể dùng last-known nếu chưa có fix mới. Luôn xem thời điểm đo và sai số. Có thể bỏ tọa độ cũ; SOS vẫn có mô tả vị trí bắt buộc.

## Lỗi thường gặp

| Lỗi | Kiểm tra |
|---|---|
| Chưa có Flutter | PATH và `flutter doctor` |
| Không thấy điện thoại | Cáp dữ liệu, USB debugging, xác nhận thiết bị |
| Không thấy peer | Cùng version/service ID, Bluetooth/Wi-Fi/Vị trí, quyền, Play services |
| Mã kết nối không hiện | Mở app cả hai máy; hết 60 giây thì dừng/bật lại |
| HTTP 401 | DRILL_KEY không đúng |
| HTTP 410 | Tin đã hết 24 giờ; tạo SOS diễn tập mới |
| HTTP 422 | Chữ ký/schema sai hoặc đồng hồ thiết bị lệch |
| Không truy cập server | URL/IP/port, VM Bridged, firewall, AP isolation |
| Màn hình khóa thì ngừng | Chính sách pin của hãng; ghi kết quả test, chưa kết luận hệ thống luôn chạy nền |

## Thu log

Tab Tiếp sức hiển thị 60 dòng gần nhất và ghi JSONL bền vững có rotation khoảng512KB. Nút “Sao chép nhật ký đo” xuất log; dán vào file trên máy tính, dùng scripts/evaluate_logs.py. Xuất sau mỗi phiên để tránh mất mẫu do rotation. Log có `CREATED`, `CONNECTED`, `STORED`, `RELAY_ACK`, `SERVER_RECEIVED`.

Chưa có bằng chứng test radio thật đi kèm bộ mã nguồn. Nhóm phải ghi model điện thoại, Android version, khoảng cách và từng lần thử.
