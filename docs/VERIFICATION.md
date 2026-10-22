# Phạm vi kiểm tra v0.2 — 2026-10-07

## Đã chạy trên môi trường tạo mã

- **37 passed**: API bằng SQLite/TestClient (28 tests gồm tham số hóa), simulator (7), chọn cấu hình Android AGP8/9 (2).
- Kiểm chứng chữ ký, sửa hash/body/signature, TTL/hop, tọa độ/schema, trùng/collision, persistence, workflow/conflict, request size, token boundary; API preview/priority/audit/stats/CSV formula guard; quota theo thời điểm nhận và duplicate exemption.
- Simulator: store/carry/forward, TTL/hop, dedup, token conservation, one-token wait, bounded buffer, priority/bandwidth, không divide-zero.
- `npm run build` **PASS**: TypeScript và Vite; không phải UI interaction test. Bundle MapLibre >500KB có warning, không chặn build.
- Python compileall **PASS**.
- HTTP smoke thật qua uvicorn/localhost với SQLite: health version0.2, model preview P1 và stats **PASS**.
- Train và export NLP **PASS**, 270 mẫu JSON inference khớp sklearn atol1e-9, group không giao nhau; macro-F1/recall/classification report trong EVALUATION.
- 60 simulation runs (3 quy mô × 10 seeds × 2 algorithms), raw CSV/JSON kèm.

Python3.12, Node24.19.0, backend dependency pins trong requirements, sklearn1.7.2, numpy2.2.6. CI mô tả Python3.12/Node22; chưa chứng minh CI được chạy ở GitHub.

## Còn phải xác minh trên máy nhóm

- Docker Compose và PostgreSQL integration v0.2: không có daemon/binary trong môi trường tạo. PostgreSQL advisory-lock quota chưa có integration test ở đây.
- Dashboard thao tác browser/visual/accessibility: chưa chạy; build pass không chứng minh giao diện mọi trình duyệt.
- Flutter analyze, Gradle/NDK compile, APK/install v0.2: chưa chạy, không có APK đã xác minh kèm. Lần trước cài Flutter tại môi trường tạo bị automatic approval review chặn truy cập metadata nội bộ, nên không thử vượt chặn đó. Dùng Flutter/Android Studio hiện có trên Windows của nhóm theo START_HERE.
- P2P thật nhiều điện thoại, API upload từ Android v0.2, foreground Redmi, GPS, pin, throughput/delay radio; chạy FIELD_TEST và điền CSV.

Chỉ ghi phần đã chạy là đã kiểm chứng. Các chức năng Android có mã nguồn và kiểm tra cấu hình Python, chưa được xác nhận hoạt động trên thiết bị. Có bug/lỗi mới khi nhóm chạy thì sửa theo log, không đặt điểm hoặc tỷ lệ hoàn thiện giả.
