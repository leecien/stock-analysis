import 'package:material_ui/material_ui.dart';

import '../notifications.dart';
import '../state.dart';

class SettingsPage extends StatefulWidget {
  const SettingsPage({super.key});
  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  late AppSettings s;
  late final TextEditingController owner, repo, branch, token, url;
  bool _obscure = true;
  bool _testing = false;
  String? _testResult;

  @override
  void initState() {
    super.initState();
    final cur = AppScope.read(context).settings;
    s = AppSettings(
      source: cur.source,
      ghOwner: cur.ghOwner,
      ghRepo: cur.ghRepo,
      ghBranch: cur.ghBranch,
      ghToken: cur.ghToken,
      customUrl: cur.customUrl,
      notifyEnabled: cur.notifyEnabled,
      notifyLevel: cur.notifyLevel,
      upIsRed: cur.upIsRed,
    );
    owner = TextEditingController(text: s.ghOwner);
    repo = TextEditingController(text: s.ghRepo);
    branch = TextEditingController(text: s.ghBranch);
    token = TextEditingController(text: s.ghToken);
    url = TextEditingController(text: s.customUrl);
  }

  @override
  void dispose() {
    for (final c in [owner, repo, branch, token, url]) {
      c.dispose();
    }
    super.dispose();
  }

  void _collect() {
    s.ghOwner = owner.text.trim();
    s.ghRepo = repo.text.trim();
    s.ghBranch = branch.text.trim().isEmpty ? 'data' : branch.text.trim();
    s.ghToken = token.text.trim();
    s.customUrl = url.text.trim();
  }

  Future<void> _test() async {
    _collect();
    setState(() {
      _testing = true;
      _testResult = null;
    });
    try {
      final body = await DataService.fetchRemote(s, 'latest');
      _testResult = '✅ 連線成功（${(body.length / 1024).toStringAsFixed(0)} KB）';
    } catch (e) {
      _testResult = '❌ $e';
    }
    if (mounted) setState(() => _testing = false);
  }

  Future<void> _save() async {
    _collect();
    final st = AppScope.read(context);
    final nav = Navigator.of(context);
    await st.updateSettings(s);
    try {
      if (s.notifyEnabled && s.source != DataSource.demo) {
        await requestNotificationPermission();
        await checkNewAlerts(notify: false); // 先記錄目前的警示，之後只通知新的
      }
      await scheduleBackgroundCheck(s);
    } catch (_) {}
    nav.pop();
  }

  @override
  Widget build(BuildContext context) {
    final remote = s.source != DataSource.demo;
    return Scaffold(
      appBar: AppBar(title: const Text('設定'), actions: [TextButton(onPressed: _save, child: const Text('儲存'))]),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        const Text('資料來源', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
        const SizedBox(height: 8),
        SegmentedButton<DataSource>(
          segments: const [
            ButtonSegment(value: DataSource.demo, label: Text('示範資料')),
            ButtonSegment(value: DataSource.github, label: Text('GitHub')),
            ButtonSegment(value: DataSource.url, label: Text('自訂網址')),
          ],
          selected: {s.source},
          onSelectionChanged: (v) => setState(() => s.source = v.first),
        ),
        const SizedBox(height: 12),
        if (s.source == DataSource.demo)
          const Text('使用 App 內建的示範資料，不需要網路。後端架好之後切換到 GitHub。',
              style: TextStyle(color: Colors.grey)),
        if (s.source == DataSource.github) ...[
          const Text('讀取後端每小時更新到 GitHub「data」分支的分析結果。私人 repo 需要 Token（只需要該 repo 的 Contents 讀取權限）。',
              style: TextStyle(color: Colors.grey, fontSize: 13)),
          const SizedBox(height: 12),
          Row(children: [
            Expanded(child: TextField(controller: owner, decoration: const InputDecoration(labelText: '帳號', border: OutlineInputBorder()))),
            const SizedBox(width: 8),
            Expanded(child: TextField(controller: repo, decoration: const InputDecoration(labelText: 'Repo', border: OutlineInputBorder()))),
          ]),
          const SizedBox(height: 10),
          TextField(controller: branch, decoration: const InputDecoration(labelText: '分支', border: OutlineInputBorder())),
          const SizedBox(height: 10),
          TextField(
            controller: token,
            obscureText: _obscure,
            decoration: InputDecoration(
              labelText: 'GitHub Token（私人 repo 才需要）',
              border: const OutlineInputBorder(),
              suffixIcon: IconButton(
                icon: Icon(_obscure ? Icons.visibility : Icons.visibility_off),
                onPressed: () => setState(() => _obscure = !_obscure),
              ),
            ),
          ),
        ],
        if (s.source == DataSource.url) ...[
          const Text('網址底下需要有 latest.json 與 history.json', style: TextStyle(color: Colors.grey, fontSize: 13)),
          const SizedBox(height: 10),
          TextField(
            controller: url,
            keyboardType: TextInputType.url,
            decoration: const InputDecoration(labelText: '網址，例如 https://example.com/data/', border: OutlineInputBorder()),
          ),
        ],
        if (remote) ...[
          const SizedBox(height: 10),
          Row(children: [
            OutlinedButton.icon(
              onPressed: _testing ? null : _test,
              icon: _testing
                  ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.wifi_tethering),
              label: const Text('測試連線'),
            ),
            const SizedBox(width: 10),
            if (_testResult != null) Expanded(child: Text(_testResult!, style: const TextStyle(fontSize: 13))),
          ]),
        ],
        const Divider(height: 36),
        const Text('通知', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('有新警示時通知我'),
          subtitle: const Text('背景約每小時檢查一次（示範資料模式不會通知）'),
          value: s.notifyEnabled,
          onChanged: (v) => setState(() => s.notifyEnabled = v),
        ),
        if (s.notifyEnabled)
          Row(children: [
            const Text('通知等級：'),
            const SizedBox(width: 8),
            DropdownButton<String>(
              value: s.notifyLevel,
              items: const [
                DropdownMenuItem(value: 'info', child: Text('全部（含關鍵字暴增）')),
                DropdownMenuItem(value: 'warning', child: Text('重要以上')),
                DropdownMenuItem(value: 'critical', child: Text('只有緊急')),
              ],
              onChanged: (v) => setState(() => s.notifyLevel = v ?? 'warning'),
            ),
          ]),
        const Divider(height: 36),
        const Text('顯示', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('紅漲綠跌（台灣習慣）'),
          subtitle: const Text('關閉則為綠漲紅跌（美國習慣）'),
          value: s.upIsRed,
          onChanged: (v) => setState(() => s.upIsRed = v),
        ),
        const Divider(height: 36),
        const Text('本 App 內容由程式與 AI 自動產生，僅供研究參考，不構成任何投資建議。',
            style: TextStyle(fontSize: 12, color: Colors.grey)),
      ]),
    );
  }
}
