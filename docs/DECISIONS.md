# Quyết định kỹ thuật cho v0.1

Đây là bước bắt đầu kế hoạch 14 tuần, không phải hoàn thành toàn bộ MVP đã đề xuất.

1. **SQLiteOpenHelper thay Room ở PoC.** Một Android core duy nhất sở hữu DB; Flutter gọi MethodChannel. Giảm cấu hình KSP/annotation processing trước khi xác minh radio; có thể chuyển Room với migration, không tạo DB thứ hai.
2. **ECDSA P-256 thay Ed25519 ở PoC.** Android Keystore hỗ trợ tạo và giữ private key EC, tương thích API 26 đã chọn; Python xác minh bằng cryptography. Ghi rõ thuật toán thực tế, không gọi đây là Ed25519.
3. **Chưa E2E encryption.** Giữ prototype dễ debug bằng dữ liệu diễn tập; không thu dữ liệu thật. Bảo mật nội dung là milestone kế tiếp sau PoC.
4. **PostgreSQL chưa PostGIS.** Lưu tọa độ trong body JSON cho marker. PostGIS chỉ thêm khi triển khai truy vấn khoảng cách/vùng/routing. Không giả định spatial index đang tồn tại.
5. **Rules không được quảng cáo là mô hình AI huấn luyện.** Chưa PhoBERT, dataset, confidence hay kết quả accuracy. UI/API ghi `rules-v0.1-no-ml`.
6. **Polling 5 giây thay SSE ban đầu.** Ít thành phần vận hành; UI hiện thời điểm cập nhật. Mất kết nối không xóa dữ liệu đang xem nhưng báo lỗi.
7. **Không tự chấp nhận mọi peer.** Người thử đối chiếu mã Nearby trên cả hai thiết bị. Tự động xác thực peer đã provisioning là hướng tiếp theo.
8. **Không deploy public.** Docker LAN cho nhóm thử; chưa HTTPS, chống spam toàn diện, RBAC từng người hay vận hành cứu hộ.

## Tài liệu chính thức tham khảo

- https://developers.google.com/nearby/connections/android/get-started
- https://developers.google.com/nearby/connections/android/manage-connections
- https://developers.google.com/nearby/connections/android/exchange-data
- https://developers.google.com/nearby/connections/strategies
- https://developer.android.com/develop/background-work/services/fgs/service-types
- https://docs.flutter.dev/platform-integration/platform-channels
- https://fastapi.tiangolo.com/tutorial/sql-databases/
- https://maplibre.org/maplibre-gl-js/docs/
- https://operations.osmfoundation.org/policies/tiles/

Versions dependencies được pin để tái lập, không quảng cáo là phiên bản mới nhất. Trước triển khai public cần rà soát cập nhật và dependency security.
