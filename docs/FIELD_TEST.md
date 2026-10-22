# Kiểm thử Android thực tế

## Chuẩn bị và định nghĩa

Ghi: model/Android/Play services, phiên bản APK, cài đặt pin, khoảng cách, nguồn điện, điều kiện Wi-Fi/Bluetooth, nhiệt độ tương đối, UTC đồng hồ. Chỉ dùng tình huống giả; không để người thử xuống nước/nguy hiểm. IDs ngẫu nhiên; tên A/B/C cho bảng kết quả. Tắt mobile data; Wi-Fi và Bluetooth vẫn bật. Không dùng Wi-Fi Internet trước bước gateway.

**Delivered** = gateway nhận `SERVER_RECEIVED` có đúng ID từ API. Không phải đội cứu hộ đã tới. Delay = thời điểm receipt − thời điểm CREATED theo log, cần đồng bộ giờ; ghi clock skew. Reception server còn có `received_at_ms` trong CSV. Delivery ratio mẫu số là tất cả ID được tạo trong cửa sổ test đã xác định, kể cả thất bại; đo tới deadline định trước (ví dụ 10 phút).

## Ma trận

| Test | Cách làm | Lặp | Điều kiện đạt ở bài diễn tập |
|---|---|---:|---|
| Trực tiếp | A/B offline, so mã, A tạo, B lưu/ACK | 10 | Cùng ID, lưu trước ACK, không cần Internet |
| Hai hop | A→B; tắt relay A; B đóng/mở; B→C; C online | 10 | C nhận hop=2, Dashboard một incident |
| Retry | Ngắt kết nối khi đang chuyển; gặp lại, xác nhận | 10 | Tin không mất, không tạo bản trùng |
| Gateway lỗi | Sai key, ngắt LAN, sửa key/khôi phục LAN | 5 | Giữ tin; chỉ mark uploaded sau receipt |
| Process restart | Force-stop sau lưu, mở app và bật relay lại | 5 | SQLite còn tin; không tự khẳng định service tự bật |
| Mã sai | Từ chối mã kết nối khác | 5 | Không chuyển DATA; lần gặp sau cần xác nhận lại |
| Hết TTL/hop | Dùng simulator/API unit tests để tạo biên | tự động | Không relay sau TTL/hop, từ chối unsigned edits |
| Nhiều tin | 20 tin P1/P2/P3, giới hạn quota 30/key/h | 5 | Có ưu tiên và P3 có cơ hội, không đánh giá thứ tự từ vài tin |
| Màn hình khóa | Khóa 30–60 phút, đo từng hãng | 3/thiết bị | Báo sống/chết thực tế, không coi thất bại là bỏ mẫu |

Khoảng cách thay đổi 1/5/10/20 m nếu môi trường an toàn. Nếu chỉ có 2 điện thoại thì chứng minh một hop; ba hop/quy mô lớn mô phỏng, không ghi như test radio thật.

## Pin

Trên cùng điện thoại: baseline app mở nhưng không relay, scanning không peer, relay có peer/tải tin. Mỗi ca 60 phút, ≥3 lần; cùng mức sáng/cấu hình/mức pin đầu, không cắm sạc, đảo thứ tự ca để giảm bias. Ghi %pin đầu/cuối, thời gian, nhiệt, số tin; %/giờ là ước lượng thô. Có thể dùng Android Battery Historian/adb batterystats nếu nhóm biết; dữ liệu power profile không tự là phép đo mAh chính xác. Không suy ra pin thực tế từ số transfers simulator.

## Thu bằng chứng

Mỗi máy: nút **Sao chép nhật ký đo**, dán file JSONL. Trên máy tính dùng `scripts/evaluate_logs.py`. Không trộn các phiên ngoài cửa sổ test; parser hiện tổng hợp mọi dòng supplied và giảm trùng theo ID, vì vậy xuất log riêng/loại dòng của phiên cũ trước khi tính. Script không phát hiện mọi dòng bị mất do rotation, nên đối chiếu số CREATED với phiếu kiểm thử. SEND_ATTEMPT là lần enqueue DATA, chưa phải payload truyền thành công; đừng dùng trực tiếp làm overhead radio.

Điền `docs/field_runs.csv`, không có dòng kết quả giả đi kèm. Xuất CSV Dashboard, chụp video A/B/C + mất mạng, lưu cấu hình phiên. Ảnh không chứa token/mật khẩu hoặc vị trí người thật.
