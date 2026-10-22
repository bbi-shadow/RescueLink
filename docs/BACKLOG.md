# Phạm vi và tiêu chí nghiệm thu

## Must (đã có mã, kiểm tra thiết bị theo FIELD_TEST)

Android tạo SOS text/GPS/needs, SQLite, Nearby P2P_CLUSTER + DTN ở tầng ứng dụng, ký ECDSA, SHA256 đúng body bytes, TTL/hop/inventory/dedup/ACK, retry/buffer có giới hạn; gateway upload idempotent; server xác minh; NLP train/evaluate/inference; Dashboard list/map/heatmap/workflow/operator priority/audit; simulator Epidemic vs binary Spray-and-Wait và báo cáo kết quả.

## Should (đã viết)

Xuất CSV, preview NLP, optimistic concurrency, quota khóa nguồn + nginx rate limit, gateway exponential backoff+jitter, nhật ký Android bền vững có giới hạn và script đo, paging, CI server/web, script cập nhật Android có backup.

## Could (ngoài bản này)

PhoBERT với bộ nhãn SOS thật được duyệt; PRoPHET; ONE traces; signed server receipt/receipt gossip; E2EE thiết kế khóa gateway; per-user accounts/RBAC, HTTPS deployment, SQL migrations quy mô production, quản lý nguồn lực/routing đường có cập nhật ngập; background tối ưu radio; PostGIS.

## Won't trong MVP 14 tuần

iOS, BLE Mesh chuẩn và bridge Android–iOS, Computer Vision/ảnh/audio/video; tự động dispatch thật; cam kết luôn giao tin/luôn chạy nền. Nearby cung cấp kết nối peer; app tự store/forward, không hứa mesh IP xuyên điện thoại. Simulator Spray-and-Wait là thuật toán so sánh, chưa là thuật toán radio Android (Android đang bounded Epidemic + weighted priority).

“100%” chỉ có nghĩa tất cả tiêu chí đã thống nhất có bằng chứng đạt; chưa có số liệu phone/P2P/pin cho v0.2 thì chưa được ghi 100% nghiệm thu. Sản phẩm vận hành cứu hộ thật cần phạm vi khác, kiểm định chuyên môn, dữ liệu, bảo mật, SLA và quy trình phối hợp.
