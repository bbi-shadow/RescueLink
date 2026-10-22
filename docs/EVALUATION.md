# Kết quả đánh giá v0.2 (2026-10-07)

## NLP — test tổng hợp, không đại diện thực địa

270 câu, 90 group; split group-disjoint seed42 60/20/20. Test54 câu từ18 group. TF-IDF chỉ fit train. So sánh text-only; chưa đo toàn bộ policy kết hợp mức khai báo/needs/low-score.

| Model | Macro-F1 | Recall P1 | Accuracy |
|---|---:|---:|---:|
| Rules từ khóa | 0.4252 | 0.1667 | 0.4444 |
| TF-IDF + Logistic Regression | 0.7593 | 0.6111 | 0.7593 |

Recall P1 thấp là hạn chế nghiêm trọng nếu dùng tự động điều phối. Model hiện chỉ hỗ trợ người trực; safety rule có thể nâng P1 khi có từ khóa/người gửi yêu cầu y tế, nhưng có false positives và chưa được đánh giá bằng tập thực địa. Baseline rất đơn giản; không kết luận model này vượt mọi baseline/PhoBERT. Tập nhỏ tổng hợp và các biến thể cùng group không độc lập hoàn toàn; không dùng kết quả này làm chứng cứ độ chính xác cứu hộ thật. SHA256, nhãn/partitions và confusion matrix trong `ai/artifacts/evaluation.json`. JSON inference khớp sklearn toàn bộ270 mẫu ở atol1e-9.

## DTN — paired random-contact simulation

10 seeds mỗi quy mô, cùng message/contact trace cho hai thuật toán ở mỗi seed. 100 messages, TTL1800s, thời gian7200s, buffer50/node, bandwidth5 payload/direction/contact, gateway0, hoplimit8; binary Spray-and-Wait budget4. Delay chỉ trên các tin delivered nên có selection bias. Overhead=(payload transfers−delivered remote messages)/delivered; không tính inventory/ACK/bytes/radio. Khi zero delivery, delay/overhead=null. Simulator không mô phỏng authentication, khoảng cách, pin hoặc multi-radio Nearby.

| Nodes | Routing | Delivery ratio mean ± SD | Delay mean (s) | Overhead mean |
|---:|---|---:|---:|---:|
| 30 | epidemic | 1.000 ± 0.000 | 261.9 | 28.95 |
| 30 | spray_wait | 0.978 ± 0.013 | 468.8 | 3.07 |
| 50 | epidemic | 1.000 ± 0.000 | 298.5 | 49.24 |
| 50 | spray_wait | 0.894 ± 0.056 | 638.4 | 3.37 |
| 100 | epidemic | 1.000 ± 0.000 | 340.3 | 100.38 |
| 100 | spray_wait | 0.686 ± 0.062 | 768.7 | 4.40 |

Trong cấu hình này Epidemic giao nhiều/nhanh hơn nhưng sao chép nhiều; Spray-and-Wait giảm overhead và mất delivery khi gateway ít gặp. Đây là kết quả mô phỏng đã chạy, không phải kết quả Android thật. Không đồng nhất Android weighted scheduling với simulator strict priority. Contacts tạo số encounter tỷ lệ nodes; cùng giả định mỗi node hoạt động đồng đều, không phải người thật khi lũ. Muốn kết luận thuật toán: thêm sparse/community/mobility traces, gateway tỷ lệ khác, workload/TTL/buffer/copy budget sweeps, paired confidence intervals, nhiều seeds và ONE nếu có thời gian. Raw runs.csv có p95, drops, expiry, hops mỗi run.

## Thực địa

Chưa có số liệu v0.2. `field_runs.csv` chỉ header để nhóm điền, không có dữ liệu dựng lên. Kiểm thử trên Redmi của bản cũ không tự chứng minh bản mới chạy hoặc truyền qua nhiều máy. Hoàn thành FIELD_TEST trước khi tuyên bố nghiệm thu.
