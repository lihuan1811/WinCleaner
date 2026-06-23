import 'package:flutter_test/flutter_test.dart';
import 'package:wincleaner_desktop/services/rule_store_service.dart';

void main() {
  test('default rule store exposes c_cleaner_plus rule packs', () {
    final packs = const RuleStoreService().packs;
    final fileNames = packs.map((pack) => pack.fileName);

    expect(fileNames, contains('common_custom_rules.json'));
    expect(fileNames, contains('rules_cn_apps.json'));
    expect(fileNames, contains('rules_dev_tools.json'));
    expect(fileNames, contains('rules_ai_tools.json'));
    expect(fileNames, contains('rules_game_platforms.json'));
    expect(fileNames, contains('bleachbit.json'));
    expect(fileNames, contains('winapp2.json'));
    expect(packs.every((pack) => pack.sourceUrl.isScheme('https')), isTrue);
  });
}
