"""Author-created exercise data, NOT disaster reports or expert medical labels."""
import csv
from pathlib import Path
SCENARIOS={
1:[
'Có người đang bị nước cuốn trôi, cần cứu ngay', 'Một người bất tỉnh và không thở sau khi ngã xuống nước',
'Người bị thương chảy máu rất nhiều không cầm được', 'Có trẻ em mắc kẹt trong căn nhà nước đang lên rất nhanh',
'Có người bị đất đá vùi lấp sau sạt lở', 'Người già đang khó thở nghiêm trọng và không thể di chuyển',
'Phụ nữ mang thai đang chuyển dạ giữa vùng ngập cần cấp cứu', 'Có người đang đuối nước ngay cạnh cầu',
'Tường nhà đang đổ và còn người bị kẹt bên trong', 'Một người bị điện giật đang bất tỉnh',
'Có người đau ngực dữ dội và ngất', 'Trẻ nhỏ đang co giật liên tục',
'Thuyền bị lật và nhiều người đang chìm dưới nước', 'Nạn nhân bị gãy chân mắc kẹt nước đã lên tới cổ',
'Chúng tôi bị kẹt trên mái nhà và mái đang sập', 'Lũ quét đang tới có người chưa thoát khỏi khe núi',
'Người bị chấn thương đầu không còn tỉnh táo', 'Một người bị bỏng nặng toàn thân',
'Có người bị đá đè lên ngực không thở được', 'Em bé tím tái không phản ứng',
'Đất đang tiếp tục sạt xuống căn nhà có người ở', 'Người bệnh ngất liên tục không đáp lại lời gọi',
'Có người ngã xuống dòng lũ chảy xiết chưa kéo lên được', 'Cây đổ đè một người đang chảy máu nặng',
'Người bị thương đang mất ý thức sau tai nạn', 'Nhiều người bị kẹt trong ô tô nước đang tràn vào',
'Có người khó thở sau khi hít khói và đã ngất', 'Cần đội y tế gấp người bệnh đã ngừng thở',
'Bờ sông sụp xuống có người đang bám vào cành cây', 'Nước dâng tới mái nhà trẻ nhỏ đang bị lạnh và lịm đi'],
2:[
'Gia đình hết nước uống cần tiếp tế trong ngày', 'Chúng tôi còn an toàn nhưng đã hết thực phẩm',
'Cần sơ tán người dân khỏi vùng ngập hiện mọi người còn an toàn', 'Có người bị thương nhẹ cần băng gạc',
'Người già cần thuốc huyết áp hiện vẫn tỉnh táo', 'Cần xuồng đưa người dân ra ngoài nước đang ổn định',
'Nhà bị cô lập cần thuốc và thực phẩm', 'Trẻ em thiếu sữa và nước sạch',
'Có người sốt cần nhân viên y tế kiểm tra', 'Cần chỗ trú tạm vì nhà bị ngập tầng dưới',
'Chúng tôi hết pin điện thoại cần sạc và đèn', 'Cần vận chuyển thuốc đến điểm trú tránh',
'Nhiều gia đình thiếu chăn áo khô sau mưa lũ', 'Đường bị chặn cần hỗ trợ di chuyển người già',
'Có người bong gân vẫn tỉnh cần hỗ trợ đi lại', 'Cần thức ăn cho nhóm đang bị cô lập',
'Cần nước sạch tại nơi sơ tán có trẻ nhỏ', 'Mọi người ở tầng cao cần đội hỗ trợ đưa đến nơi an toàn',
'Nhà ngập cần hỗ trợ sơ tán trong hôm nay', 'Thuốc điều trị hằng ngày đã hết cần tiếp tế',
'Người dân đang trú ở trường học thiếu lương thực', 'Cần băng vệ sinh và đồ dùng cho trẻ em',
'Xin hỗ trợ máy bơm và thiết bị chiếu sáng trong ngày', 'Người bị trầy xước cần sát trùng vết thương',
'Chúng tôi có nơi trú nhưng chưa có đồ ăn hôm nay', 'Đề nghị cứu trợ nước và thuốc cho thôn bị chia cắt',
'Đường ra ngoài bị ngập cần xe đưa người bệnh đi khám', 'Cần đội đến kiểm tra nhà có dấu hiệu nứt mọi người đã ra ngoài',
'Người dân cần nơi ở tạm sau khi đã rời vùng nguy hiểm', 'Cần hỗ trợ liên lạc với gia đình tại điểm sơ tán'],
3:[
'Xin thông tin đường đi tới điểm tập kết ngày mai', 'Mọi người an toàn muốn biết lịch phân phát hàng cứu trợ',
'Đăng ký làm tình nguyện viên dọn vệ sinh sau lũ', 'Xin danh sách số điện thoại đội hỗ trợ',
'Cần thông tin lịch khôi phục điện khu vực', 'Muốn biết vị trí kho tiếp nhận đồ quyên góp',
'Đề nghị thu gom rác sau khi nước đã rút', 'Xin hướng dẫn bảo quản đồ dùng sau ngập',
'Mọi người đã an toàn cần xác nhận điểm báo danh', 'Đăng ký xe hỗ trợ vận chuyển vào ngày mai',
'Nhờ cung cấp thông báo tình hình thời tiết', 'Cần bản đồ các điểm trú tránh để tham khảo',
'Xin lịch họp tổ dân phố về khắc phục hậu quả', 'Đề nghị hỗ trợ sửa đường sau khi lũ đã rút',
'Muốn đăng ký đóng góp thực phẩm cho địa phương', 'Xin thông tin thủ tục nhận hỗ trợ sửa nhà',
'Gia đình đã được sơ tán an toàn muốn cập nhật thông tin', 'Cần lịch vệ sinh trường học sau bão',
'Nhờ xác nhận địa chỉ trung tâm điều phối', 'Xin hướng dẫn đăng ký nhu cầu hỗ trợ dài hạn',
'Đề nghị kiểm kê thiệt hại sau khi tình hình ổn định', 'Đăng ký nhận dụng cụ dọn nhà vào tuần sau',
'Xin danh sách điểm cấp phát quần áo trong tuần', 'Muốn tìm nhóm tình nguyện hỗ trợ cộng đồng',
'Chúng tôi đã có đủ lương thực xin cập nhật lịch cứu trợ', 'Xin thông tin cách sử dụng ứng dụng báo tin',
'Nhờ thông báo khi cầu được mở lại chúng tôi đang an toàn', 'Cần biết nơi nộp hồ sơ thống kê thiệt hại',
'Đăng ký hỗ trợ phân loại hàng quyên góp', 'Đề nghị kiểm tra hệ thống thoát nước sau mùa lũ']}
if __name__=='__main__':
 p=Path(__file__).parent/'data/sos_demo.csv'
 with p.open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['text','priority','group_id','source']);w.writeheader()
  for label,lines in SCENARIOS.items():
   for i,s in enumerate(lines):
    for prefix in ['', 'Diễn tập tại thôn A: ', 'Tin nhắn từ điểm B: ']:
     w.writerow(dict(text=prefix+s,priority=label,group_id=f'P{label}-{i:02}',source='author_created_synthetic'))
 print(p)
