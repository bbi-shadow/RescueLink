# NLP triage có thể tái lập

Model: TF-IDF word 1–2 gram + Logistic Regression balanced; chạy server bằng phép nhân tuyến tính từ JSON, không load pickle. Lựa chọn nhẹ, giải thích được và phù hợp nhóm 2 người. PhoBERT là hướng mở rộng sau khi có dữ liệu đủ tốt, không gọi model này là PhoBERT.

`data/sos_demo.csv`: 270 câu do nhóm công cụ tạo, 90 tình huống độc lập, mỗi tình huống 3 biến thể tiền tố. Không thu thập lời cầu cứu thật, không chứa PII. Đây là dataset smoke-test để chứng minh pipeline; các nhãn không được chuyên gia y tế xác nhận. Script `build_demo_data.py` tái tạo dữ liệu.

Chia theo **group_id** 60/20/20, stratified, seed 42: train 162, validation 54, test 54. Vectorizer chỉ fit train; không trộn biến thể cùng tình huống sang test. Validation lưu để nghiên cứu tiếp; C=4 và ngưỡng .60 đang là lựa chọn cố định, chưa tối ưu/calibrate trên validation. Test chỉ đánh giá model text-only, không trộn mức người dùng khai báo hoặc medical override vào F1.

```bash
pip install -r ai/requirements.txt
python ai/train.py
python ai/train.py --data ai/data/my_reviewed_data.csv --out ai/artifacts/new-model
```

CSV phải có `text,priority,group_id,source`. P1: dấu hiệu nguy hiểm tính mạng; P2: nhu cầu hỗ trợ thiết yếu/sơ tán chưa đủ chứng cứ P1; P3: thông tin/phối hợp. Khi chưa rõ, nhãn `ambiguous` trong bộ thu thập riêng để chuyên gia xét lại, không ép về P3 trong tập train. Công cụ train chỉ nhận nhãn 1/2/3 đã được duyệt.

Bổ sung dữ liệu: tối thiểu vài trăm tình huống đa dạng, người gán nhãn thứ hai độc lập, thống kê Cohen's kappa, giải quyết bất đồng; group các biến thể của cùng sự kiện. Tách địa bàn/nguồn/sự kiện và người diễn đạt nếu có; kiểm tra không có dữ liệu test trong train. Không tự download mạng xã hội rồi mặc định được phép dùng. Dataset tiếng Việt phân loại tin tức/sentiment không trực tiếp là nhãn SOS; cần đánh giá chuyển miền và quyền sử dụng trước.

Outputs:
- `triage_model.json`: vocabulary, IDF, weights, version, SHA256 dataset.
- `evaluation.json`: group partitions, confusion matrix, precision/recall/F1 từng lớp, macro-F1 và baseline rules trên cùng test.
- Train kiểm tra toàn bộ 270 dòng: xác suất JSON inference khớp sklearn (atol 1e-9).

Inference API: `/api/v1/triage/preview` chỉ admin; không lưu incident. `confidence` là softmax score **chưa được calibration**, không là xác suất nạn nhân nguy kịch. Score thấp hoặc không có token đã biết → hàng chờ P2, có thể nâng ưu tiên theo từ khóa nguy hiểm, nhu cầu y tế và mức người gửi. Model không tự sửa priority điều phối; tất cả yêu cầu cần người kiểm tra. Rủi ro: phủ định, tiếng địa phương, sai chính tả, câu nói mỉa, context thiếu, distribution shift; tập tổng hợp nhỏ không đo hết các rủi ro này.

Đánh giá ngoài test hiện có: thêm câu có phủ định, nhiều nhu cầu, không dấu, phương ngữ, cực ngắn, thời điểm “đã an toàn”; báo recall P1 và false-negative P1, đánh giá abstention/coverage; có thể calibration bằng validation thật. Không tối ưu rồi báo lại trên chính test cũ như một test độc lập.

Tài liệu chính thức:
- https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html
- https://scikit-learn.org/stable/modules/feature_extraction.html#text-feature-extraction
- https://scikit-learn.org/stable/modules/cross_validation.html#cross-validation-iterators-for-grouped-data
