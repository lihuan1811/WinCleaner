class AccountStoreFile {
  const AccountStoreFile([String? path]);

  Future<bool> exists() async => false;

  Future<String> readAsString() async => '';

  Future<void> writeAsString(String content) async {}
}

AccountStoreFile defaultAccountStoreFile() => const AccountStoreFile();

String createPlatformDeviceSeed() {
  return 'web-${DateTime.now().microsecondsSinceEpoch}';
}
