import 'dart:convert';

import 'package:flutter/services.dart' show rootBundle;
import 'package:http/http.dart' as http;
import 'package:material_ui/material_ui.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'models.dart';

/// 資料來源：示範資料（內建）、GitHub（data 分支）、自訂網址
enum DataSource { demo, github, url }

class AppSettings {
  DataSource source;
  String ghOwner, ghRepo, ghBranch, ghToken, customUrl, notifyLevel;
  bool notifyEnabled, upIsRed;

  AppSettings({
    this.source = DataSource.demo,
    this.ghOwner = 'leecien',
    this.ghRepo = 'stock-analysis',
    this.ghBranch = 'data',
    this.ghToken = '',
    this.customUrl = '',
    this.notifyEnabled = true,
    this.notifyLevel = 'warning',
    this.upIsRed = true,
  });

  static Future<AppSettings> load() async {
    final p = await SharedPreferences.getInstance();
    return AppSettings(
      source: DataSource.values.firstWhere((e) => e.name == p.getString('source'),
          orElse: () => DataSource.demo),
      ghOwner: p.getString('ghOwner') ?? 'leecien',
      ghRepo: p.getString('ghRepo') ?? 'stock-analysis',
      ghBranch: p.getString('ghBranch') ?? 'data',
      ghToken: p.getString('ghToken') ?? '',
      customUrl: p.getString('customUrl') ?? '',
      notifyEnabled: p.getBool('notifyEnabled') ?? true,
      notifyLevel: p.getString('notifyLevel') ?? 'warning',
      upIsRed: p.getBool('upIsRed') ?? true,
    );
  }

  Future<void> save() async {
    final p = await SharedPreferences.getInstance();
    await p.setString('source', source.name);
    await p.setString('ghOwner', ghOwner.trim());
    await p.setString('ghRepo', ghRepo.trim());
    await p.setString('ghBranch', ghBranch.trim());
    await p.setString('ghToken', ghToken.trim());
    await p.setString('customUrl', customUrl.trim());
    await p.setBool('notifyEnabled', notifyEnabled);
    await p.setString('notifyLevel', notifyLevel);
    await p.setBool('upIsRed', upIsRed);
  }
}

class FetchResult {
  final String body;
  final bool fromCache;
  final String? warning;
  FetchResult(this.body, {this.fromCache = false, this.warning});
}

/// 讀取 latest.json / history.json
class DataService {
  static Future<String> fetchRemote(AppSettings s, String name) async {
    late Uri uri;
    final headers = <String, String>{};
    if (s.source == DataSource.github) {
      uri = Uri.https('api.github.com', '/repos/${s.ghOwner}/${s.ghRepo}/contents/public/$name.json',
          {'ref': s.ghBranch});
      headers['Accept'] = 'application/vnd.github.raw+json';
      headers['X-GitHub-Api-Version'] = '2022-11-28';
      if (s.ghToken.isNotEmpty) headers['Authorization'] = 'Bearer ${s.ghToken}';
    } else {
      var base = s.customUrl.trim();
      if (!base.endsWith('/')) base = '$base/';
      uri = Uri.parse('$base$name.json');
    }
    final r = await http.get(uri, headers: headers).timeout(const Duration(seconds: 30));
    if (r.statusCode == 401 || r.statusCode == 403) {
      throw Exception('沒有權限讀取（${r.statusCode}），請檢查 GitHub Token');
    }
    if (r.statusCode == 404) {
      throw Exception('找不到資料（404）：請確認 repo、分支名稱，以及後端是否已經執行過');
    }
    if (r.statusCode != 200) throw Exception('下載失敗：HTTP ${r.statusCode}');
    return utf8.decode(r.bodyBytes);
  }

  static Future<FetchResult> load(AppSettings s, String name) async {
    if (s.source == DataSource.demo) {
      return FetchResult(await rootBundle.loadString('assets/demo/$name.json'));
    }
    final prefs = await SharedPreferences.getInstance();
    final key = 'cache_${s.source.name}_$name';
    try {
      final body = await fetchRemote(s, name);
      jsonDecode(body); // 確認格式正確才存快取
      await prefs.setString(key, body);
      return FetchResult(body);
    } catch (e) {
      final cached = prefs.getString(key);
      if (cached != null) {
        return FetchResult(cached, fromCache: true, warning: '無法更新，顯示上次的資料（$e）');
      }
      rethrow;
    }
  }
}

/// 全 App 共用狀態
class AppState extends ChangeNotifier {
  AppSettings settings = AppSettings();
  Latest? latest;
  HistoryData? history;
  bool loading = false;
  bool historyLoading = false;
  String? error;
  String? warning;
  String? historyError;

  Future<void> init() async {
    settings = await AppSettings.load();
    await refresh();
  }

  Future<void> refresh() async {
    loading = true;
    error = null;
    notifyListeners();
    try {
      final r = await DataService.load(settings, 'latest');
      latest = Latest.fromJson(jm(jsonDecode(r.body)));
      warning = r.warning;
    } catch (e) {
      error = '$e';
    }
    loading = false;
    notifyListeners();
  }

  Future<void> loadHistory({bool force = false}) async {
    if (historyLoading || (history != null && !force)) return;
    historyLoading = true;
    historyError = null;
    notifyListeners();
    try {
      final r = await DataService.load(settings, 'history');
      history = HistoryData.fromJson(jm(jsonDecode(r.body)));
    } catch (e) {
      historyError = '$e';
    }
    historyLoading = false;
    notifyListeners();
  }

  Future<void> updateSettings(AppSettings s) async {
    settings = s;
    await s.save();
    history = null;
    await refresh();
  }
}

class AppScope extends InheritedNotifier<AppState> {
  const AppScope({super.key, required AppState state, required super.child}) : super(notifier: state);

  static AppState of(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<AppScope>()!.notifier!;

  /// 不訂閱變化（可在 initState 使用）
  static AppState read(BuildContext context) =>
      context.getInheritedWidgetOfExactType<AppScope>()!.notifier!;
}
