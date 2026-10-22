import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

const native = MethodChannel('rescuelink/native');
const needLabels = {'medical':'Y tế','evacuation':'Sơ tán','food':'Thực phẩm','water':'Nước uống','other':'Khác'};
void main() => runApp(const RescueApp());

class RescueApp extends StatelessWidget {
  const RescueApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'RescueLink · Diễn tập', debugShowCheckedModeBanner: false,
    theme: ThemeData(useMaterial3: true, colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xff195442)),
      scaffoldBackgroundColor: const Color(0xfff3f5ef),
      inputDecorationTheme: const InputDecorationTheme(border: OutlineInputBorder(), filled: true, fillColor: Colors.white)),
    home: const HomePage(),
  );
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});
  @override State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final text = TextEditingController();
  final place = TextEditingController();
  final count = TextEditingController(text: '1');
  final baseUrl = TextEditingController();
  final drillKey = TextEditingController();
  final form = GlobalKey<FormState>();
  Map<String, dynamic> state = {};
  Map<String, dynamic>? position;
  final Set<String> needs = {'evacuation'};
  int priority = 2;
  int tab = 0;
  bool busy = false;
  bool polling = false;
  bool pairing = false;
  bool gettingLocation = false;
  String? error;
  Timer? timer;

  @override void initState() {
    super.initState();
    loadSettings();
    refresh();
    timer = Timer.periodic(const Duration(seconds: 2), (_) => refresh());
  }
  @override void dispose() {
    timer?.cancel();
    for (final controller in [text, place, count, baseUrl, drillKey]) { controller.dispose(); }
    super.dispose();
  }
  void notice(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }
  Future<void> loadSettings() async {
    try {
      final settings = await native.invokeMapMethod<String, dynamic>('getSettings');
      if (!mounted) return;
      baseUrl.text = settings?['base_url'] as String? ?? '';
      drillKey.text = settings?['drill_key'] as String? ?? '';
    } catch (_) { /* The state request displays the platform error. */ }
  }
  Future<void> refresh() async {
    if (polling) return;
    polling = true;
    try {
      final raw = await native.invokeMethod<String>('state');
      final data = jsonDecode(raw!) as Map<String, dynamic>;
      if (!mounted) return;
      setState(() { state = data; error = null; });
      final pending = (data['pending'] as List?) ?? [];
      if (!pairing && pending.isNotEmpty) { unawaited(confirmPeer(Map<String,dynamic>.from(pending.first as Map))); }
    } on MissingPluginException {
      if (mounted) setState(() => error = 'Bản này chạy trên Android thật. Hãy chạy bootstrap_mobile.py trước khi build.');
    } catch (e) {
      if (mounted) setState(() => error = 'Không đọc được Android core: $e');
    } finally { polling = false; }
  }
  Future<void> confirmPeer(Map<String,dynamic> peer) async {
    pairing = true;
    try {
      final accepted = await showDialog<bool>(context: context, barrierDismissible: false, builder: (ctx) => AlertDialog(
        title: const Text('Xác thực thiết bị gần đây'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [Text('So sánh mã với ${peer['name']}'),
          const SizedBox(height: 20), Text('${peer['code']}', style: const TextStyle(fontSize: 36, fontWeight: FontWeight.bold)),
          const SizedBox(height: 15), const Text('Chỉ chấp nhận khi mã trên cả hai máy giống nhau. Cả hai người đều cần xác nhận trong 60 giây.')]),
        actions: [TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Từ chối')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Mã trùng khớp'))],
      ));
      await native.invokeMethod('pair', {'endpoint_id': peer['endpoint_id'], 'accept': accepted == true});
    } catch (e) { notice('Không xác nhận được: $e'); }
    finally { pairing = false; }
  }
  Future<void> act(Future<void> Function() action) async {
    if (busy) return;
    setState(() => busy = true);
    try { await action(); await refresh(); }
    catch (e) { notice(e is PlatformException ? (e.message ?? e.code) : '$e'); }
    finally { if (mounted) setState(() => busy = false); }
  }
  Future<void> locate() async {
    setState(() => gettingLocation = true);
    try {
      final location = await native.invokeMapMethod<String, dynamic>('location');
      if (mounted && location != null) setState(() => position = Map<String,dynamic>.from(location));
    } catch (e) { notice(e is PlatformException ? (e.message ?? e.code) : '$e'); }
    finally { if (mounted) setState(() => gettingLocation = false); }
  }
  Future<void> createSOS() async {
    if (!(form.currentState?.validate() ?? false)) return;
    await act(() async {
      final data = <String, dynamic>{'text': text.text.trim(), 'location_text': place.text.trim(),
        'priority': priority, 'people_count': int.parse(count.text), 'needs': needs.toList(), ...?position};
      await native.invokeMethod('createSOS', jsonEncode(data));
      text.clear();
      notice('Đã lưu SOS trên máy. Chưa có nghĩa trung tâm hoặc đội cứu hộ đã nhận.');
      if (mounted) setState(() => tab = 1);
    });
  }
  String time(dynamic ms) => ms == null ? 'Chưa có' : DateTime.fromMillisecondsSinceEpoch((ms as num).toInt()).toLocal().toString().split('.').first;
  Color priorityColor(int p) => p == 1 ? const Color(0xffb84932) : p == 2 ? const Color(0xff9b7528) : const Color(0xff367650);
  Widget box(Widget child) => Container(margin: const EdgeInsets.only(bottom: 16), padding: const EdgeInsets.all(18),
    decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: const Color(0xffe0e6dc))), child: child);

  @override Widget build(BuildContext context) {
    final messages = (state['messages'] as List?) ?? [];
    final running = state['running'] == true;
    final peers = (state['peers'] as Map?) ?? {};
    return Scaffold(
      appBar: AppBar(title: const Text('✳ RescueLink', style: TextStyle(fontWeight: FontWeight.w800)),
        actions: [Container(margin: const EdgeInsets.only(right: 14), padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(color: const Color(0xfff5e4b8), borderRadius: BorderRadius.circular(5)),
          child: const Text('DIỄN TẬP', style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold)))]),
      body: SafeArea(child: RefreshIndicator(onRefresh: refresh, child: ListView(padding: const EdgeInsets.all(18), children: [
        if (error != null) box(Text(error!, style: const TextStyle(color: Colors.red))),
        if (tab == 0) ...[
          const Text('Gửi một lời nhờ giúp.', style: TextStyle(fontSize: 27, fontWeight: FontWeight.w800)),
          const Padding(padding: EdgeInsets.symmetric(vertical: 10), child: Text('SOS được lưu ngay cả khi không có Internet. Chỉ dùng tình huống diễn tập, không nhập dữ liệu cá nhân thật.')),
          Form(key: form, child: Column(children: [
            box(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Mức độ người gửi khai báo', style: TextStyle(fontWeight: FontWeight.bold)),
              const SizedBox(height: 12),
              DropdownButtonFormField<int>(value: priority, items: const [DropdownMenuItem(value: 1, child: Text('P1 · Cần hỗ trợ khẩn cấp')), DropdownMenuItem(value: 2, child: Text('P2 · Cần hỗ trợ sớm')), DropdownMenuItem(value: 3, child: Text('P3 · Hỗ trợ thông thường'))], onChanged: (v) => setState(() => priority = v ?? 2)),
              const SizedBox(height: 16), TextFormField(controller: text, maxLength: 1000, minLines: 3, maxLines: 6, decoration: const InputDecoration(labelText: 'Mô tả tình huống diễn tập', hintText: 'Có bao nhiêu người, đang gặp vấn đề gì?'), validator: (v) => (v?.trim().length ?? 0) < 3 ? 'Nhập ít nhất 3 ký tự' : null),
              const SizedBox(height: 8), TextFormField(controller: count, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Số người cần hỗ trợ'), validator: (v) { final n = int.tryParse(v ?? ''); return n == null || n < 1 || n > 1000 ? 'Nhập từ 1 đến 1000' : null; }),
              const SizedBox(height: 12), Wrap(spacing: 8, children: needLabels.entries.map((e) => FilterChip(label: Text(e.value), selected: needs.contains(e.key), onSelected: (checked) => setState(() { if (checked) { needs.add(e.key); } else { needs.remove(e.key); } }))).toList()),
            ])),
            box(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              TextFormField(controller: place, maxLength: 250, decoration: const InputDecoration(labelText: 'Mô tả vị trí', hintText: 'Thôn, xã, điểm dễ nhận biết…'), validator: (v) => (v?.trim().isEmpty ?? true) ? 'Nhập mô tả để vẫn tìm được khi thiếu GPS' : null),
              OutlinedButton.icon(onPressed: gettingLocation ? null : locate, icon: const Icon(Icons.my_location), label: Text(gettingLocation ? 'Đang lấy GPS…' : 'Lấy vị trí GPS')),
              if (position != null) ...[Text('${position!['latitude']}, ${position!['longitude']}'), Text('Sai số ${position!['accuracy_m']} m · đo ${time(position!['location_captured_at_ms'])}', style: const TextStyle(fontSize: 11)), TextButton(onPressed: () => setState(() => position = null), child: const Text('Bỏ tọa độ này'))]
              else const Text('Chưa có GPS vẫn lưu được SOS bằng mô tả vị trí.', style: TextStyle(fontSize: 12)),
            ])),
            SizedBox(width: double.infinity, child: FilledButton.icon(onPressed: busy ? null : createSOS, icon: const Icon(Icons.sos), label: Padding(padding: const EdgeInsets.all(14), child: Text(busy ? 'Đang lưu…' : 'LƯU SOS DIỄN TẬP')))),
          ])),
        ],
        if (tab == 1) ...[
          const Text('Tin đang được tiếp sức', style: TextStyle(fontSize: 25, fontWeight: FontWeight.w800)),
          const SizedBox(height: 12), const Text('Hiển thị tối đa 200 tin gần nhất. Tin đã hết hạn không được chuyển tiếp.'),
          const SizedBox(height: 16),
          if (messages.isEmpty) box(const Text('Chưa có SOS. Tạo tin hoặc kết nối một thiết bị khác để nhận.')),
          ...messages.map((raw) {
            final m = Map<String,dynamic>.from(raw as Map);
            final b = Map<String,dynamic>.from(m['body'] as Map);
            final label = m['uploaded'] == true ? 'Server đã nhận' : m['expired'] == true ? 'Đã hết hạn chuyển tiếp' : m['relay_acked'] == true ? 'Một relay đã lưu' : 'Đang lưu trên máy';
            return box(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [Text('P${b['priority']}', style: TextStyle(color: priorityColor(b['priority'] as int), fontWeight: FontWeight.bold)), const SizedBox(width: 10), Expanded(child: Text(label, style: const TextStyle(fontSize: 12))), Text(m['own'] == true ? 'Của tôi' : 'Chuyển tiếp', style: const TextStyle(fontSize: 10))]),
              const SizedBox(height: 12), Text('${b['location_text']}', style: const TextStyle(fontWeight: FontWeight.bold)), const SizedBox(height: 5), Text('${b['text']}'),
              const SizedBox(height: 10), Text('Tạo: ${time(b['created_at_ms'])}', style: const TextStyle(fontSize: 11)),
              Text('Hết hạn: ${time(b['expires_at_ms'])}', style: const TextStyle(fontSize: 11)),
              if ((m['error'] as String? ?? '').isNotEmpty) Text('${m['error']}', style: const TextStyle(fontSize: 11, color: Colors.deepOrange)),
              Text('ID ${(m['message_id'] as String).substring(0, 12)}…', style: const TextStyle(fontSize: 10, color: Colors.grey)),
            ]));
          }),
        ],
        if (tab == 2) ...[
          const Text('Trở thành một điểm nối.', style: TextStyle(fontSize: 25, fontWeight: FontWeight.w800)), const SizedBox(height: 12),
          box(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(state['status'] as String? ?? 'Đang khởi tạo…'), const SizedBox(height: 12),
            Text('Mã máy: ${(state['node_id'] as String? ?? '').length >= 12 ? (state['node_id'] as String).substring(0,12) : '…'}', style: const TextStyle(fontSize: 12)),
            Text('Đang kết nối ${peers.length} máy'),
            for (final peer in peers.values) Text('• $peer', style: const TextStyle(fontSize: 12)),
            const SizedBox(height: 12), Wrap(spacing: 8, children: [
              OutlinedButton(onPressed: busy ? null : () => act(() async { final ok = await native.invokeMethod<bool>('permissions'); notice(ok == true ? 'Đã có quyền cần thiết' : 'Chưa đủ quyền; xem lại Cài đặt ứng dụng'); }), child: const Text('1. Cấp quyền')),
              FilledButton(onPressed: busy ? null : () => act(() async { if (!running) { final ok = await native.invokeMethod<bool>('permissions'); if (ok != true) { notice('Cần cấp quyền trước khi bật'); return; } } await native.invokeMethod(running ? 'stopRelay' : 'startRelay'); }), child: Text(running ? 'Dừng tiếp sức' : '2. Bật tiếp sức')),
            ]),
            const SizedBox(height: 10), const Text('Bật Bluetooth và Wi-Fi. Lần đầu gặp nhau, mở app trên cả hai máy và đối chiếu mã. Không tự tiếp tục sau Force stop.', style: TextStyle(fontSize: 12)),
          ])),
          box(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Gateway → trung tâm', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)), const SizedBox(height: 8),
            const Text('Chỉ máy có nhiệm vụ upload cần cấu hình. Máy gửi và relay có thể để trống.', style: TextStyle(fontSize: 12)), const SizedBox(height: 14),
            TextField(controller: baseUrl, keyboardType: TextInputType.url, decoration: const InputDecoration(labelText: 'URL máy chủ', hintText: 'http://192.168.1.10:8080')), const SizedBox(height: 12),
            TextField(controller: drillKey, obscureText: true, autocorrect: false, decoration: const InputDecoration(labelText: 'DRILL_KEY từ file .env')), const SizedBox(height: 12),
            Wrap(spacing: 8, children: [OutlinedButton(onPressed: busy ? null : () => act(() async { await native.invokeMethod('saveSettings', {'base_url': baseUrl.text, 'drill_key': drillKey.text}); notice('Đã lưu cấu hình gateway'); }), child: const Text('Lưu cấu hình')),
              FilledButton(onPressed: busy ? null : () => act(() async { final n = await native.invokeMethod<int>('sync'); notice('Đồng bộ $n SOS. Xem lỗi từng tin nếu chưa gửi được.'); }), child: const Text('Đồng bộ ngay'))]),
            const Text('Tự thử upload mỗi 15 giây khi tiếp sức đang bật. HTTP chỉ dành cho debug trong mạng LAN tin cậy.', style: TextStyle(fontSize: 11)),
          ])),
          box(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [const Text('Nhật ký phiên', style: TextStyle(fontWeight: FontWeight.bold)), const SizedBox(height: 10),
            OutlinedButton(onPressed: busy ? null : () => act(() async { final log = await native.invokeMethod<String>('exportMeasurements'); await Clipboard.setData(ClipboardData(text: log ?? '')); notice('Đã sao chép nhật ký đo JSONL; dán vào file trên máy tính.'); }), child: const Text('Sao chép nhật ký đo')),
            SelectableText(((state['logs'] as List?) ?? []).reversed.join('\n'), style: const TextStyle(fontSize: 10, fontFamily: 'monospace'))])),
        ],
        const SizedBox(height: 20), const Text('v0.1 · Có chữ ký số, CHƯA mã hóa đầu cuối. Chỉ dùng dữ liệu diễn tập. Ảnh, âm thanh và AI huấn luyện chưa có trong bản này.', style: TextStyle(fontSize: 11, color: Colors.grey)),
      ]))),
      bottomNavigationBar: NavigationBar(selectedIndex: tab, onDestinationSelected: (i) => setState(() => tab = i), destinations: const [
        NavigationDestination(icon: Icon(Icons.sos), label: 'Tạo SOS'),
        NavigationDestination(icon: Icon(Icons.inbox_outlined), label: 'Hộp tin'),
        NavigationDestination(icon: Icon(Icons.hub_outlined), label: 'Tiếp sức'),
      ]),
    );
  }
}
