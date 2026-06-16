import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:wincleaner_desktop/services/ad_block_service.dart';

void main() {
  test('enables and disables managed hosts ad-block entries', () async {
    final tempDir = await Directory.systemTemp.createTemp('hosts-test-');
    addTearDown(() => tempDir.delete(recursive: true));

    final hostsFile = File('${tempDir.path}/hosts')
      ..writeAsStringSync('127.0.0.1 localhost\n');
    final service = AdBlockService(
      hostsFile: hostsFile,
      flushDns: false,
      backupDirectory: Directory('${tempDir.path}/backup'),
    );

    expect(await service.isEnabled(), isFalse);

    final enabled = await service.enable(domains: const ['ads.example.com']);

    expect(enabled.enabled, isTrue);
    expect(enabled.blockedDomains, 1);
    expect(hostsFile.readAsStringSync(), contains('0.0.0.0 ads.example.com'));
    expect(Directory('${tempDir.path}/backup').listSync(), isNotEmpty);

    final disabled = await service.disable();

    expect(disabled.enabled, isFalse);
    expect(hostsFile.readAsStringSync(), isNot(contains('ads.example.com')));
    expect(hostsFile.readAsStringSync(), contains('127.0.0.1 localhost'));
  });
}
