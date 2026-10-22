# Kế hoạch nghiệm thu PoC

## Bảng ghi thực nghiệm

Ghi cho từng lượt: mã test, thời gian, máy A/B/C (model, Android, pin), điều kiện Internet, khoảng cách, thời điểm tạo/nhận relay/nhận server, kết quả, lỗi, log.

| ID | Thử nghiệm | Điều kiện đạt |
|---|---|---|
| P01 | A→B offline | B có đúng nội dung và message ID; A nhận relay ACK |
| P02 | A gặp B rồi B gặp C | C nhận khi A đã rời mạng |
| P03 | Đóng/mở B | Tin đã lưu còn nguyên |
| P04 | C chưa có server, sau đó có | Tin chờ được upload khi đồng bộ |
| P05 | Hai gateway upload cùng gói | Một row incident, một audit RECEIVED |
| P06 | Tắt kết nối giữa lúc truyền | Không báo ACK sai; có thể thử lại |
| P07 | Đổi nội dung một byte | Signature/hash validation từ chối |
| P08 | Tin mới quá TTL | Không truyền/không tạo mới trên server |
| P09 | Đồng hồ sai +10 phút | Hiện lỗi; sửa đồng hồ rồi tạo tin mới |
| P10 | Force-stop relay | Không giả định tiếp tục; mở lại vẫn còn DB |
| P11 | Khóa màn hình 10/30/60 phút | Ghi số tin và pin, kể cả kết quả thất bại |
| P12 | Không có peer | Tin ở local, không báo trung tâm đã nhận |
| P13 | URL sai hoặc drill key sai | Tin còn; lỗi xuất hiện, không mark uploaded |
| P14 | Hai operator sửa cùng version | Một thao tác thắng, thao tác cũ trả 409 |

Ít nhất 20 lượt cho P01/P02 nếu thời gian cho phép; báo n và khoảng tin cậy. Đồng bộ giờ thiết bị trước đo end-to-end. Bản v0.1 không có cơ chế clock correction.

## Không trộn các loại bằng chứng

- Unit/API tests: chứng minh logic phần được test.
- Build/analyze: chứng minh mã qua compiler/analyzer trong phiên bản tương ứng.
- Điện thoại thật: xác nhận quyền, lifecycle và radio.
- ONE Simulator (giai đoạn sau): xu hướng quy mô dưới giả định.

Không thay số liệu máy thật bằng dữ liệu seed hoặc ảnh screenshot dashboard.

## Metric giai đoạn này

- SOS duy nhất tới server / SOS tạo.
- Độ trễ A→B, A→server; tách thời gian đợi gặp node.
- Số bản ghi trùng server phải bằng 0 trong test idempotency.
- Pin %/giờ: relay bật so với tắt cùng điều kiện.
- Số lần phải dừng/bật lại discovery.

Chưa có claim về độ chính xác ML vì chưa huấn luyện mô hình.
