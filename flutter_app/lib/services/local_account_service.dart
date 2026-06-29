import 'dart:async';
import 'dart:convert';

import 'package:crypto/crypto.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;

import 'account_storage.dart';

class AccountException implements Exception {
  const AccountException(this.message);

  final String message;

  @override
  String toString() => message;
}

class LocalSubscription {
  const LocalSubscription({
    required this.planName,
    required this.activatedAt,
    required this.expiresAt,
  });

  final String planName;
  final DateTime activatedAt;
  final DateTime expiresAt;

  bool get isActive => expiresAt.isAfter(DateTime.now());

  int get remainingDays {
    final days = expiresAt.difference(DateTime.now()).inDays;
    return days < 0 ? 0 : days + 1;
  }

  LocalSubscription copyWith({
    String? planName,
    DateTime? activatedAt,
    DateTime? expiresAt,
  }) {
    return LocalSubscription(
      planName: planName ?? this.planName,
      activatedAt: activatedAt ?? this.activatedAt,
      expiresAt: expiresAt ?? this.expiresAt,
    );
  }

  Map<String, Object?> toJson() {
    return {
      'planName': planName,
      'activatedAt': activatedAt.toIso8601String(),
      'expiresAt': expiresAt.toIso8601String(),
    };
  }

  factory LocalSubscription.fromJson(Map<String, Object?> json) {
    return LocalSubscription(
      planName: (json['planName'] as String?) ?? '专业会员',
      activatedAt: DateTime.tryParse((json['activatedAt'] as String?) ?? '') ??
          DateTime.fromMillisecondsSinceEpoch(0),
      expiresAt: DateTime.tryParse((json['expiresAt'] as String?) ?? '') ??
          DateTime.fromMillisecondsSinceEpoch(0),
    );
  }
}

class LocalUser {
  const LocalUser({
    required this.email,
    required this.displayName,
    required this.passwordHash,
    required this.createdAt,
    this.subscription,
    this.redeemedCodes = const [],
  });

  final String email;
  final String displayName;
  final String passwordHash;
  final DateTime createdAt;
  final LocalSubscription? subscription;
  final List<String> redeemedCodes;

  LocalUser copyWith({
    String? email,
    String? displayName,
    String? passwordHash,
    DateTime? createdAt,
    LocalSubscription? subscription,
    List<String>? redeemedCodes,
  }) {
    return LocalUser(
      email: email ?? this.email,
      displayName: displayName ?? this.displayName,
      passwordHash: passwordHash ?? this.passwordHash,
      createdAt: createdAt ?? this.createdAt,
      subscription: subscription ?? this.subscription,
      redeemedCodes: redeemedCodes ?? this.redeemedCodes,
    );
  }

  Map<String, Object?> toJson() {
    return {
      'email': email,
      'displayName': displayName,
      'passwordHash': passwordHash,
      'createdAt': createdAt.toIso8601String(),
      'subscription': subscription?.toJson(),
      'redeemedCodes': redeemedCodes,
    };
  }

  factory LocalUser.fromJson(Map<String, Object?> json) {
    return LocalUser(
      email: (json['email'] as String?) ?? '',
      displayName: (json['displayName'] as String?) ?? '',
      passwordHash: (json['passwordHash'] as String?) ?? '',
      createdAt: DateTime.tryParse((json['createdAt'] as String?) ?? '') ??
          DateTime.fromMillisecondsSinceEpoch(0),
      subscription: json['subscription'] is Map
          ? LocalSubscription.fromJson(
              Map<String, Object?>.from(json['subscription'] as Map),
            )
          : null,
      redeemedCodes: ((json['redeemedCodes'] as List?) ?? const [])
          .map((value) => value.toString())
          .toList(),
    );
  }
}

class LocalAccountState {
  const LocalAccountState({
    this.user,
    required this.deviceId,
  });

  factory LocalAccountState.empty({String deviceId = 'local-device'}) {
    return LocalAccountState(deviceId: deviceId);
  }

  final LocalUser? user;
  final String deviceId;

  bool get isSignedIn => user != null;
  bool get isPremium => user?.subscription?.isActive ?? false;
  String get displayName => user?.displayName ?? '未登录';
  String get email => user?.email ?? '';
  String get planLabel {
    if (isPremium) {
      return user!.subscription!.planName;
    }
    return isSignedIn ? 'Free' : 'Guest';
  }

  DateTime? get expiresAt => user?.subscription?.expiresAt;
  int get remainingDays => user?.subscription?.remainingDays ?? 0;

  LocalAccountState copyWith({
    LocalUser? user,
    String? deviceId,
  }) {
    return LocalAccountState(
      user: user ?? this.user,
      deviceId: deviceId ?? this.deviceId,
    );
  }
}

class CardRedemptionResult {
  const CardRedemptionResult({
    required this.state,
    required this.message,
  });

  final LocalAccountState state;
  final String message;
}

class LocalAccountService {
  LocalAccountService({
    AccountStoreFile? storeFile,
    LocalAccountState? initialState,
    DateTime Function()? now,
    Uri? apiBaseUri,
    http.Client? httpClient,
    bool? useRemoteApi,
    Duration requestTimeout = const Duration(milliseconds: 900),
  })  : _storeFile = kIsWeb ? storeFile : storeFile ?? _defaultStoreFile(),
        _now = now ?? DateTime.now,
        _apiBaseUri = apiBaseUri ?? _defaultApiBaseUri,
        _httpClient = httpClient ?? http.Client(),
        _ownsHttpClient = httpClient == null,
        _useRemoteApi = useRemoteApi ?? initialState == null,
        _requestTimeout = requestTimeout,
        _memoryStore = initialState == null
            ? kIsWeb
                ? _AccountStore.empty(_createDeviceId())
                : null
            : _AccountStore.fromState(initialState);

  static final Uri _defaultApiBaseUri = Uri.parse(
    const String.fromEnvironment(
      'WINCLEANER_API_BASE_URL',
      defaultValue: 'http://127.0.0.1:8000',
    ),
  );

  static const demoCardCodes = [
    'WINCLEANER-VIP-30D',
    'WINCLEANER-VIP-365D',
    'WINCLEANER-TEAM-365D',
  ];

  final AccountStoreFile? _storeFile;
  final DateTime Function() _now;
  final Uri _apiBaseUri;
  final http.Client _httpClient;
  final bool _ownsHttpClient;
  final bool _useRemoteApi;
  final Duration _requestTimeout;
  _AccountStore? _memoryStore;

  Future<LocalAccountState> loadState() async {
    final store = await _loadStore();
    if (_useRemoteApi) {
      final remoteState = await _tryRemoteState(store.deviceId);
      if (remoteState != null) {
        await _saveStore(_AccountStore.fromState(remoteState));
        return remoteState;
      }
    }
    return store.currentState;
  }

  Future<LocalAccountState> register({
    required String email,
    required String password,
    required String displayName,
  }) async {
    final normalizedEmail = _normalizeEmail(email);
    final trimmedName = displayName.trim();
    _validateEmail(normalizedEmail);
    _validatePassword(password);

    final store = await _loadStore();
    if (_useRemoteApi) {
      final remoteState = await _tryRemotePostState(
        '/api/auth/register',
        {
          'email': normalizedEmail,
          'password': password,
          'displayName': trimmedName,
          'deviceId': store.deviceId,
        },
      );
      if (remoteState != null) {
        await _saveStore(_AccountStore.fromState(remoteState));
        return remoteState;
      }
    }

    if (store.users.any((user) => user.email == normalizedEmail)) {
      throw const AccountException('这个邮箱已经注册，请直接登录。');
    }

    final user = LocalUser(
      email: normalizedEmail,
      displayName:
          trimmedName.isEmpty ? normalizedEmail.split('@').first : trimmedName,
      passwordHash: _hashPassword(normalizedEmail, password),
      createdAt: _now(),
    );
    final next = store.copyWith(
      users: [...store.users, user],
      currentEmail: normalizedEmail,
    );
    await _saveStore(next);
    return next.currentState;
  }

  Future<LocalAccountState> login({
    required String email,
    required String password,
  }) async {
    final normalizedEmail = _normalizeEmail(email);
    _validateEmail(normalizedEmail);
    _validatePassword(password);

    final store = await _loadStore();
    if (_useRemoteApi) {
      final remoteState = await _tryRemotePostState(
        '/api/auth/login',
        {
          'email': normalizedEmail,
          'password': password,
          'deviceId': store.deviceId,
        },
      );
      if (remoteState != null) {
        await _saveStore(_AccountStore.fromState(remoteState));
        return remoteState;
      }
    }

    final user = store.userByEmail(normalizedEmail);
    if (user == null ||
        user.passwordHash != _hashPassword(normalizedEmail, password)) {
      throw const AccountException('邮箱或密码不正确。');
    }

    final next = store.copyWith(currentEmail: normalizedEmail);
    await _saveStore(next);
    return next.currentState;
  }

  Future<LocalAccountState> logout() async {
    final store = await _loadStore();
    if (_useRemoteApi) {
      final remoteState = await _tryRemotePostState(
        '/api/auth/logout',
        {'deviceId': store.deviceId},
      );
      if (remoteState != null) {
        await _saveStore(_AccountStore.fromState(remoteState));
        return remoteState;
      }
    }

    final next = store.copyWith(currentEmail: '');
    await _saveStore(next);
    return next.currentState;
  }

  Future<CardRedemptionResult> redeemCard(String rawCode) async {
    final code = rawCode.trim().toUpperCase();
    if (code.isEmpty) {
      throw const AccountException('卡密不能为空。');
    }

    final store = await _loadStore();
    if (_useRemoteApi) {
      final remoteResult = await _tryRemoteRedeemCard(store.deviceId, code);
      if (remoteResult != null) {
        await _saveStore(_AccountStore.fromState(remoteResult.state));
        return remoteResult;
      }
    }

    final plan = _cardPlans[code];
    if (plan == null) {
      throw const AccountException('卡密不存在或格式不正确。');
    }

    final user = store.currentUser;
    if (user == null) {
      throw const AccountException('请先登录或注册账户，再兑换会员卡。');
    }
    if (user.redeemedCodes.contains(code)) {
      throw const AccountException('这张会员卡已经兑换过。');
    }

    final now = _now();
    final currentExpiry = user.subscription?.expiresAt;
    final startAt = currentExpiry != null && currentExpiry.isAfter(now)
        ? currentExpiry
        : now;
    final subscription = LocalSubscription(
      planName: plan.planName,
      activatedAt: now,
      expiresAt: startAt.add(Duration(days: plan.days)),
    );
    final updatedUser = user.copyWith(
      subscription: subscription,
      redeemedCodes: [...user.redeemedCodes, code],
    );
    final next = store.replaceUser(updatedUser);
    await _saveStore(next);
    return CardRedemptionResult(
      state: next.currentState,
      message: '${plan.planName}已开通，有效期 ${plan.days} 天。',
    );
  }

  void dispose() {
    if (_ownsHttpClient) {
      _httpClient.close();
    }
  }

  Future<LocalAccountState?> _tryRemoteState(String deviceId) async {
    final body = await _tryRemoteRequest(
      () => _httpClient.get(
        _api('/api/account/state/${Uri.encodeComponent(deviceId)}'),
      ),
    );
    return body == null ? null : _stateFromApiJson(body);
  }

  Future<LocalAccountState?> _tryRemotePostState(
    String path,
    Map<String, Object?> payload,
  ) async {
    final body = await _tryRemoteRequest(
      () => _httpClient.post(
        _api(path),
        headers: const {'content-type': 'application/json'},
        body: jsonEncode(payload),
      ),
    );
    return body == null ? null : _stateFromApiJson(body);
  }

  Future<CardRedemptionResult?> _tryRemoteRedeemCard(
    String deviceId,
    String code,
  ) async {
    final body = await _tryRemoteRequest(
      () => _httpClient.post(
        _api('/api/cards/redeem'),
        headers: const {'content-type': 'application/json'},
        body: jsonEncode({
          'deviceId': deviceId,
          'code': code,
        }),
      ),
    );
    if (body == null) {
      return null;
    }
    return CardRedemptionResult(
      state: _stateFromApiJson(body),
      message: (body['message'] as String?) ?? '会员卡已兑换。',
    );
  }

  Future<Map<String, Object?>?> _tryRemoteRequest(
    Future<http.Response> Function() send,
  ) async {
    try {
      final response = await send().timeout(_requestTimeout);
      return _decodeApiBody(response);
    } on AccountException {
      rethrow;
    } on TimeoutException {
      return null;
    } catch (_) {
      return null;
    }
  }

  Map<String, Object?> _decodeApiBody(http.Response response) {
    Object? decoded;
    try {
      decoded = jsonDecode(response.body);
    } catch (_) {
      decoded = null;
    }
    if (response.statusCode >= 200 &&
        response.statusCode < 300 &&
        decoded is Map) {
      return Map<String, Object?>.from(decoded);
    }
    if (response.statusCode >= 400) {
      throw AccountException(_apiErrorMessage(response, decoded));
    }
    throw const AccountException('账户服务返回了异常响应。');
  }

  String _apiErrorMessage(http.Response response, Object? decoded) {
    if (decoded is Map) {
      final detail = decoded['detail'];
      if (detail is String && detail.isNotEmpty) {
        return detail;
      }
      if (detail != null) {
        return detail.toString();
      }
    }
    return '账户服务请求失败（${response.statusCode}）。';
  }

  LocalAccountState _stateFromApiJson(Map<String, Object?> json) {
    final user = json['user'];
    return LocalAccountState(
      deviceId: (json['deviceId'] as String?) ?? _createDeviceId(),
      user: user is Map
          ? LocalUser.fromJson(Map<String, Object?>.from(user))
          : null,
    );
  }

  Uri _api(String path) {
    final basePath = _apiBaseUri.path.endsWith('/')
        ? _apiBaseUri.path.substring(0, _apiBaseUri.path.length - 1)
        : _apiBaseUri.path;
    final nextPath = path.startsWith('/') ? path : '/$path';
    return _apiBaseUri.replace(path: '$basePath$nextPath');
  }

  Future<_AccountStore> _loadStore() async {
    if (_memoryStore != null) {
      return _memoryStore!;
    }
    final storeFile = _storeFile;
    if (storeFile == null || !await storeFile.exists()) {
      return _AccountStore.empty(_createDeviceId());
    }
    try {
      final raw = await storeFile.readAsString();
      final decoded = jsonDecode(raw);
      if (decoded is Map) {
        return _AccountStore.fromJson(Map<String, Object?>.from(decoded));
      }
    } catch (_) {
      return _AccountStore.empty(_createDeviceId());
    }
    return _AccountStore.empty(_createDeviceId());
  }

  Future<void> _saveStore(_AccountStore store) async {
    if (_memoryStore != null) {
      _memoryStore = store;
      return;
    }
    final storeFile = _storeFile;
    if (storeFile == null) {
      _memoryStore = store;
      return;
    }
    await storeFile.writeAsString(
      const JsonEncoder.withIndent('  ').convert(store.toJson()),
    );
  }

  static AccountStoreFile _defaultStoreFile() => defaultAccountStoreFile();

  static String _normalizeEmail(String email) => email.trim().toLowerCase();

  static void _validateEmail(String email) {
    if (!email.contains('@') || !email.contains('.')) {
      throw const AccountException('请输入有效邮箱。');
    }
  }

  static void _validatePassword(String password) {
    if (password.length < 6) {
      throw const AccountException('密码至少需要 6 位。');
    }
  }

  static String _hashPassword(String email, String password) {
    return sha256.convert(utf8.encode('$email::$password')).toString();
  }

  static String _createDeviceId() {
    final raw = createPlatformDeviceSeed();
    return sha256.convert(utf8.encode(raw)).toString().substring(0, 12);
  }
}

class _CardPlan {
  const _CardPlan(this.planName, this.days);

  final String planName;
  final int days;
}

const _cardPlans = {
  'WINCLEANER-VIP-30D': _CardPlan('专业会员', 30),
  'WINCLEANER-VIP-365D': _CardPlan('专业会员', 365),
  'WINCLEANER-TEAM-365D': _CardPlan('企业会员', 365),
};

class _AccountStore {
  const _AccountStore({
    required this.deviceId,
    required this.users,
    required this.currentEmail,
  });

  factory _AccountStore.empty(String deviceId) {
    return _AccountStore(deviceId: deviceId, users: const [], currentEmail: '');
  }

  factory _AccountStore.fromState(LocalAccountState state) {
    return _AccountStore(
      deviceId: state.deviceId,
      users: state.user == null ? const [] : [state.user!],
      currentEmail: state.user?.email ?? '',
    );
  }

  final String deviceId;
  final List<LocalUser> users;
  final String currentEmail;

  LocalUser? get currentUser => userByEmail(currentEmail);

  LocalAccountState get currentState {
    return LocalAccountState(user: currentUser, deviceId: deviceId);
  }

  LocalUser? userByEmail(String email) {
    for (final user in users) {
      if (user.email == email) {
        return user;
      }
    }
    return null;
  }

  _AccountStore copyWith({
    String? deviceId,
    List<LocalUser>? users,
    String? currentEmail,
  }) {
    return _AccountStore(
      deviceId: deviceId ?? this.deviceId,
      users: users ?? this.users,
      currentEmail: currentEmail ?? this.currentEmail,
    );
  }

  _AccountStore replaceUser(LocalUser user) {
    return copyWith(
      users: [
        for (final item in users)
          if (item.email == user.email) user else item,
      ],
      currentEmail: user.email,
    );
  }

  Map<String, Object?> toJson() {
    return {
      'deviceId': deviceId,
      'currentEmail': currentEmail,
      'users': users.map((user) => user.toJson()).toList(),
    };
  }

  factory _AccountStore.fromJson(Map<String, Object?> json) {
    return _AccountStore(
      deviceId: (json['deviceId'] as String?) ??
          LocalAccountService._createDeviceId(),
      currentEmail: (json['currentEmail'] as String?) ?? '',
      users: ((json['users'] as List?) ?? const [])
          .whereType<Map>()
          .map((entry) => LocalUser.fromJson(Map<String, Object?>.from(entry)))
          .where((user) => user.email.isNotEmpty)
          .toList(),
    );
  }
}
