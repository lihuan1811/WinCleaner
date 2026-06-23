import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';

class RulePack {
  const RulePack({
    required this.name,
    required this.category,
    required this.description,
    required this.fileName,
    required this.sourceUrl,
  });

  final String name;
  final String category;
  final String description;
  final String fileName;
  final Uri sourceUrl;
}

class RulePackDownloadResult {
  const RulePackDownloadResult({
    required this.file,
    required this.bytes,
  });

  final File file;
  final int bytes;
}

class RuleStoreService {
  const RuleStoreService();

  List<RulePack> get packs => defaultPacks();

  Future<RulePackDownloadResult> downloadRulePack(
    RulePack pack,
    Directory targetDirectory,
  ) async {
    await targetDirectory.create(recursive: true);

    final client = HttpClient();
    try {
      final request = await client.getUrl(pack.sourceUrl);
      final response = await request.close();
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw HttpException(
          '规则包下载失败，HTTP ${response.statusCode}',
          uri: pack.sourceUrl,
        );
      }

      final bytes = await consolidateHttpClientResponseBytes(response);
      jsonDecode(utf8.decode(bytes));

      final file = File('${targetDirectory.path}${Platform.pathSeparator}'
          '${_safeFileName(pack.fileName)}');
      await file.writeAsBytes(bytes, flush: true);
      return RulePackDownloadResult(file: file, bytes: bytes.length);
    } finally {
      client.close(force: true);
    }
  }

  static List<RulePack> defaultPacks() {
    const base =
        'https://raw.githubusercontent.com/Kiowx/c_cleaner_plus/main/config';
    return [
      RulePack(
        name: '通用应用缓存',
        category: '通用规则',
        description: 'VS Code、Cursor、Discord、OBS、Steam、Slack 等常见缓存。',
        fileName: 'common_custom_rules.json',
        sourceUrl: Uri.parse('$base/common_custom_rules.json'),
      ),
      RulePack(
        name: '国产软件',
        category: '应用规则',
        description: '面向常见国产软件的缓存和日志清理规则。',
        fileName: 'rules_cn_apps.json',
        sourceUrl: Uri.parse('$base/rules_cn_apps.json'),
      ),
      RulePack(
        name: '开发工具',
        category: '开发规则',
        description: 'IDE、SDK、包管理器和开发工具缓存规则。',
        fileName: 'rules_dev_tools.json',
        sourceUrl: Uri.parse('$base/rules_dev_tools.json'),
      ),
      RulePack(
        name: 'AI 工具',
        category: 'AI 规则',
        description: 'AI 客户端和相关工具的缓存规则。',
        fileName: 'rules_ai_tools.json',
        sourceUrl: Uri.parse('$base/rules_ai_tools.json'),
      ),
      RulePack(
        name: '游戏平台',
        category: '游戏规则',
        description: 'Steam、Epic 等游戏平台缓存规则。',
        fileName: 'rules_game_platforms.json',
        sourceUrl: Uri.parse('$base/rules_game_platforms.json'),
      ),
      RulePack(
        name: 'BleachBit 兼容规则',
        category: '兼容规则',
        description: '来自 c_cleaner_plus 配置目录的 BleachBit 风格规则。',
        fileName: 'bleachbit.json',
        sourceUrl: Uri.parse('$base/bleachbit.json'),
      ),
      RulePack(
        name: 'Winapp2 兼容规则',
        category: '兼容规则',
        description: '面向更多 Windows 软件的 winapp2 风格规则。',
        fileName: 'winapp2.json',
        sourceUrl: Uri.parse('$base/winapp2.json'),
      ),
    ];
  }

  static String _safeFileName(String fileName) {
    final clean = fileName.replaceAll(RegExp(r'[\\/:*?"<>|]'), '_');
    if (!clean.endsWith('.json')) {
      throw ArgumentError('规则包必须是 json 文件: $fileName');
    }
    return clean;
  }
}
