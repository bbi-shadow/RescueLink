# Protocol v1 — drill-only

## Envelope

```json
{
  "message_id": "64 lowercase hex characters",
  "body_b64": "base64 of exact UTF-8 JSON bytes",
  "public_key_b64": "base64 DER SubjectPublicKeyInfo, EC P-256",
  "signature_b64": "base64 ASN.1 DER ECDSA signature",
  "hop_count": 0
}
```

`message_id = SHA256(raw_body_bytes)`.

Chữ ký: `ECDSA-P256-SHA256(UTF8("RescueLink/v1:") || raw_body_bytes)`.

Không parse rồi serialize lại body để xác minh. Android tạo JSON một lần và giữ nguyên bytes qua tất cả relay/retry. Public key fingerprint trong body phải khớp DER key bên ngoài.

`incident_id` UUID ngẫu nhiên nằm trong body, loại bỏ phụ thuộc chỉ vào User_ID + timestamp. MVP chỉ có event tạo SOS; chưa sửa incident offline. Một incident ID gắn với message khác sẽ bị server trả 409.

Body chi tiết nằm trong model `backend/app/protocol.py::SOSBody`. `is_drill` bắt buộc `true`. Không hỗ trợ chuyển sang dữ liệu thật chỉ bằng đổi một flag.

## Các frame P2P

- `INVENTORY {ids:[...]}`: tối đa 100 ID/trang. Bản v0.1 không dùng Bloom filter.
- `DATA {envelope:{...}}`: một SOS text, tối đa 30 KB/frame.
- `STORED_ACK {message_id:...}`: gửi sau khi DB commit; không tương đương server receipt.

Mỗi peer chỉ một DATA đang chờ ACK. Timeout 20 giây; tick mỗi 15 giây kiểm tra và gửi lại. Payload transport success không được tính là ACK lưu trữ.

Relay tăng hop_count trước gửi. Node ở hop limit vẫn có thể upload trực tiếp tới server nhưng không chuyển P2P thêm. Hop_count chưa có bảo vệ chống relay ác ý; không nằm trong chữ ký nguồn.

Server chỉ nhận tin mới còn TTL. Gửi lại tin đã commit vẫn trả receipt cũ dù lúc retry đã quá hạn — giúp xử lý mất ACK mà không tạo bản ghi khác.

## Dữ liệu và trạng thái

- Local `uploaded` chỉ được đánh dấu khi nhận API response khớp message ID.
- Chưa có signed receipt lan truyền giữa peer.
- Server lưu SOS độc lập với TTL truyền; TTL hết không tự đóng incident.
- `NEW → VERIFIED → ASSIGNED → RESOLVED`; cần version khớp và đội khi phân công.
- Audit ghi actor là operator demo chung; chưa phải hệ thống định danh nhân sự.

## Giới hạn

Signature không phải encryption. SHA-256 không phải encryption. Base64 không phải encryption.

Body/GPS có thể đọc bởi relay và ai lấy được packet; bản này chỉ dành cho dữ liệu thử nghiệm. Trước dữ liệu thật phải thêm AEAD/envelope encryption, provisioning khóa nhận, HTTPS và tài khoản riêng.

TTL dựa đồng hồ wall clock đã đồng bộ trước test. Không công bố tương thích Bundle Protocol v7.
