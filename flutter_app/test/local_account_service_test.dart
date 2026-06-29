import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:wincleaner_desktop/services/account_storage.dart';
import 'package:wincleaner_desktop/services/local_account_service.dart';

void main() {
  test('registers, logs in, redeems a local member card and persists state',
      () async {
    final directory =
        await Directory.systemTemp.createTemp('wincleaner_account');
    addTearDown(() => directory.delete(recursive: true));
    final storeFile = File('${directory.path}/account.json');
    final now = DateTime.now();

    final service = LocalAccountService(
      storeFile: AccountStoreFile(storeFile.path),
      now: () => now,
      useRemoteApi: false,
    );

    final registered = await service.register(
      email: 'Admin@Example.com',
      password: '123456',
      displayName: 'Administrator',
    );

    expect(registered.isSignedIn, isTrue);
    expect(registered.email, 'admin@example.com');
    expect(registered.isPremium, isFalse);

    final redemption = await service.redeemCard('wincleaner-vip-30d');

    expect(redemption.state.isPremium, isTrue);
    expect(redemption.state.planLabel, '专业会员');
    expect(redemption.state.expiresAt, now.add(const Duration(days: 30)));

    await service.logout();
    final restoredService = LocalAccountService(
      storeFile: AccountStoreFile(storeFile.path),
      useRemoteApi: false,
    );
    final loggedIn = await restoredService.login(
      email: 'admin@example.com',
      password: '123456',
    );

    expect(loggedIn.isSignedIn, isTrue);
    expect(loggedIn.isPremium, isTrue);
    expect(loggedIn.user!.redeemedCodes, contains('WINCLEANER-VIP-30D'));
  });

  test('rejects duplicate card redemption and unauthenticated redemption',
      () async {
    final service = LocalAccountService(
      initialState: LocalAccountState.empty(deviceId: 'test-device'),
      useRemoteApi: false,
    );

    await expectLater(
      service.redeemCard('WINCLEANER-VIP-30D'),
      throwsA(isA<AccountException>()),
    );

    await service.register(
      email: 'team@example.com',
      password: '123456',
      displayName: 'Team',
    );
    await service.redeemCard('WINCLEANER-VIP-30D');

    await expectLater(
      service.redeemCard('WINCLEANER-VIP-30D'),
      throwsA(isA<AccountException>()),
    );
  });

  test('uses FastAPI account API when a backend is available', () async {
    final requestedPaths = <String>[];
    final now = DateTime.utc(2030, 1, 1);
    final client = MockClient((request) async {
      requestedPaths.add(request.url.path);
      if (request.url.path == '/api/auth/register') {
        final payload = jsonDecode(request.body) as Map<String, Object?>;
        return http.Response(
          jsonEncode({
            'deviceId': payload['deviceId'],
            'user': {
              'email': 'admin@example.com',
              'displayName': 'Administrator',
              'createdAt': now.toIso8601String(),
              'subscription': null,
              'redeemedCodes': <String>[],
            },
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      }
      if (request.url.path == '/api/cards/redeem') {
        return http.Response(
          jsonEncode({
            'deviceId': 'api-device',
            'message': '专业会员已开通，有效期 30 天。',
            'user': {
              'email': 'admin@example.com',
              'displayName': 'Administrator',
              'createdAt': now.toIso8601String(),
              'subscription': {
                'planName': '专业会员',
                'activatedAt': now.toIso8601String(),
                'expiresAt':
                    now.add(const Duration(days: 30)).toIso8601String(),
              },
              'redeemedCodes': ['WINCLEANER-VIP-30D'],
            },
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      }
      return http.Response('{"detail":"not found"}', 404);
    });

    final service = LocalAccountService(
      initialState: LocalAccountState.empty(deviceId: 'api-device'),
      apiBaseUri: Uri.parse('http://api.test'),
      httpClient: client,
      useRemoteApi: true,
    );

    final registered = await service.register(
      email: 'Admin@Example.com',
      password: '123456',
      displayName: 'Administrator',
    );
    final redemption = await service.redeemCard('wincleaner-vip-30d');

    expect(registered.email, 'admin@example.com');
    expect(redemption.state.isPremium, isTrue);
    expect(
        redemption.state.user!.redeemedCodes, contains('WINCLEANER-VIP-30D'));
    expect(requestedPaths, contains('/api/auth/register'));
    expect(requestedPaths, contains('/api/cards/redeem'));
  });

  test('does not fallback locally when backend returns a business error',
      () async {
    final now = DateTime.utc(2026, 1, 1);
    final client = MockClient((request) async {
      return http.Response(
        jsonEncode({'detail': '这张会员卡已经兑换过。'}),
        409,
        headers: {'content-type': 'application/json'},
      );
    });

    final service = LocalAccountService(
      initialState: LocalAccountState(
        deviceId: 'api-device',
        user: LocalUser(
          email: 'admin@example.com',
          displayName: 'Administrator',
          passwordHash: 'remote',
          createdAt: now,
        ),
      ),
      apiBaseUri: Uri.parse('http://api.test'),
      httpClient: client,
      useRemoteApi: true,
    );

    await expectLater(
      service.redeemCard('WINCLEANER-VIP-30D'),
      throwsA(
        isA<AccountException>().having(
          (error) => error.message,
          'message',
          '这张会员卡已经兑换过。',
        ),
      ),
    );
  });
}
