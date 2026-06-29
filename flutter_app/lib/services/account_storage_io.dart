import 'dart:io';

class AccountStoreFile {
  AccountStoreFile(String path) : _file = File(path);

  AccountStoreFile.fromFile(File file) : _file = file;

  final File _file;

  Future<bool> exists() => _file.exists();

  Future<String> readAsString() => _file.readAsString();

  Future<void> writeAsString(String content) async {
    await _file.parent.create(recursive: true);
    await _file.writeAsString(content);
  }
}

AccountStoreFile defaultAccountStoreFile() {
  if (Platform.isWindows) {
    final appData = Platform.environment['APPDATA'];
    if (appData != null && appData.isNotEmpty) {
      return AccountStoreFile('$appData\\WinCleaner\\account.json');
    }
  }
  final home = Platform.environment['HOME'] ?? Directory.current.path;
  return AccountStoreFile('$home/.wincleaner/account.json');
}

String createPlatformDeviceSeed() {
  return '${Platform.localHostname}-${DateTime.now().microsecondsSinceEpoch}';
}
