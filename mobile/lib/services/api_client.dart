import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import '../models/api_models.dart';
import '../models/server_endpoint.dart';
import 'tls_identity_verifier.dart';

class ApiException implements Exception {
  const ApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

class UnauthorizedException extends ApiException {
  const UnauthorizedException([
    super.message = 'This device is no longer authorized.',
  ]) : super(statusCode: HttpStatus.unauthorized);
}

class IdentityMismatchException extends ApiException {
  const IdentityMismatchException({
    required this.expected,
    this.actual,
  }) : super(
            'The Windows PC identity changed. Pair again only if this was intentional.');

  final String expected;
  final String? actual;
}

abstract interface class PhoneRemoteApiClient {
  Future<ServerInfo> getInfo();

  Future<PairingSession> requestPairing();

  Future<PairingResult> completePairing({
    required String sessionId,
    required String code,
    required String deviceName,
    required String platform,
  });

  Future<ServerStatus> getStatus();

  Future<List<ConfiguredApp>> getApps();

  Future<void> launchApp(String appId);

  Future<void> sendAction(String action);

  Future<void> sendMouseMove(double dx, double dy);

  Future<void> sendMouseClick({String button = 'left'});

  Future<void> sendMouseDoubleClick();

  Future<void> sendMouseWheel(double delta);

  Future<void> sendText(String text);

  Future<void> sendPowerAction(String action);

  void close();
}

abstract interface class ApiClientFactory {
  PhoneRemoteApiClient create(
    ServerEndpoint endpoint, {
    String? trustedIdentity,
    String? expectedServerId,
    String? credential,
  });
}

class HttpApiClientFactory implements ApiClientFactory {
  const HttpApiClientFactory({this.timeout = const Duration(seconds: 8)});

  final Duration timeout;

  @override
  PhoneRemoteApiClient create(
    ServerEndpoint endpoint, {
    String? trustedIdentity,
    String? expectedServerId,
    String? credential,
  }) {
    return HttpPhoneRemoteApiClient(
      endpoint: endpoint,
      trustedIdentity: trustedIdentity,
      expectedServerId: expectedServerId,
      credential: credential,
      timeout: timeout,
    );
  }
}

class HttpPhoneRemoteApiClient implements PhoneRemoteApiClient {
  HttpPhoneRemoteApiClient({
    required this.endpoint,
    this.trustedIdentity,
    this.expectedServerId,
    this.credential,
    this.timeout = const Duration(seconds: 8),
    TlsIdentityVerifier verifier = const TlsIdentityVerifier(),
  }) : _verifier = verifier {
    _httpClient = HttpClient();
    _httpClient.badCertificateCallback = (certificate, host, port) {
      if (host != endpoint.host || port != endpoint.port) {
        return false;
      }
      final expected = trustedIdentity;
      if (expected == null) {
        // Initial pairing is scoped to this endpoint. The response is accepted
        // only after its advertised fingerprints match this exact certificate.
        return true;
      }
      final actual = _fingerprintsFor(certificate).identity;
      return _sameFingerprint(expected, actual);
    };
  }

  final ServerEndpoint endpoint;
  final String? trustedIdentity;
  final String? expectedServerId;
  final String? credential;
  final Duration timeout;
  final TlsIdentityVerifier _verifier;
  late final HttpClient _httpClient;
  String? _cachedCertificatePem;
  CertificateFingerprints? _cachedFingerprints;
  static const int _maximumIconBytes = 2 * 1024 * 1024;
  static const int _iconDownloadWorkers = 4;

  @override
  Future<ServerInfo> getInfo() async {
    final response = await _send('GET', '/info');
    final info = ServerInfo.fromJson(response.body);
    if (info.apiVersion != 1) {
      throw ApiException(
        'This PC uses API v${info.apiVersion}. Update Phone Remote on your phone or PC.',
      );
    }
    if (!_sameFingerprint(
          info.identityFingerprint,
          response.fingerprints.identity,
        ) ||
        !_sameFingerprint(
          info.certificateFingerprint,
          response.fingerprints.certificate,
        )) {
      throw IdentityMismatchException(
        expected: info.identityFingerprint,
        actual: response.fingerprints.identity,
      );
    }
    final expectedIdentity = trustedIdentity;
    if (expectedIdentity != null &&
        !_sameFingerprint(expectedIdentity, info.identityFingerprint)) {
      throw IdentityMismatchException(
        expected: expectedIdentity,
        actual: info.identityFingerprint,
      );
    }
    final serverId = expectedServerId;
    if (serverId != null && serverId != info.serverId) {
      throw const ApiException(
        'The Windows PC server ID changed. Pair again to continue.',
      );
    }
    return info;
  }

  @override
  Future<PairingSession> requestPairing() async {
    final response =
        await _send('POST', '/pair/request', body: const <String, Object?>{});
    return PairingSession.fromJson(response.body);
  }

  @override
  Future<PairingResult> completePairing({
    required String sessionId,
    required String code,
    required String deviceName,
    required String platform,
  }) async {
    final response = await _send(
      'POST',
      '/pair/complete',
      body: <String, Object?>{
        'sessionId': sessionId,
        'code': code,
        'deviceName': deviceName,
        'platform': platform,
      },
    );
    return PairingResult.fromJson(response.body);
  }

  @override
  Future<ServerStatus> getStatus() async {
    final response = await _send('GET', '/status', authenticated: true);
    final status = ServerStatus.fromJson(response.body);
    _verifyServer(status.serverId, status.apiVersion);
    return status;
  }

  @override
  Future<List<ConfiguredApp>> getApps() async {
    final response = await _send('GET', '/apps', authenticated: true);
    final rawApps = response.body['apps'];
    if (rawApps is! List<Object?>) {
      throw const ApiException('The Windows PC returned an invalid app list.');
    }
    final apps = rawApps.map((value) {
      if (value is! Map<String, Object?>) {
        throw const FormatException('Configured app must be an object.');
      }
      return ConfiguredApp.fromJson(value);
    }).toList();
    var nextIndex = 0;
    Future<void> downloadNext() async {
      while (nextIndex < apps.length) {
        final index = nextIndex++;
        final app = apps[index];
        try {
          final bytes = await _getIcon(app.icon);
          apps[index] = app.withIconBytes(bytes);
        } on IdentityMismatchException {
          rethrow;
        } on Object {
          // A missing or malformed icon must not hide an otherwise usable app.
        }
      }
    }

    await Future.wait(<Future<void>>[
      for (var worker = 0;
          worker < _iconDownloadWorkers && worker < apps.length;
          worker += 1)
        downloadNext(),
    ]);
    return List<ConfiguredApp>.unmodifiable(apps);
  }

  Future<Uint8List> _getIcon(String value) async {
    final path = Uri.tryParse(value);
    if (path == null || !path.path.startsWith('/app-icons/')) {
      throw const FormatException('App icon path is invalid.');
    }
    try {
      final request =
          await _httpClient.getUrl(endpoint.resourceUri(path)).timeout(timeout);
      final token = credential;
      if (token != null && token.isNotEmpty) {
        request.headers.set(HttpHeaders.authorizationHeader, 'Bearer $token');
      }
      final response = await request.close().timeout(timeout);
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw ApiException(
          'The Windows PC did not return the app icon.',
          statusCode: response.statusCode,
        );
      }
      final certificate = response.certificate;
      if (certificate == null) {
        throw const ApiException(
            'The Windows PC did not provide a TLS certificate.');
      }
      final fingerprints = _fingerprintsFor(certificate);
      final expected = trustedIdentity;
      if (expected != null &&
          !_sameFingerprint(expected, fingerprints.identity)) {
        throw IdentityMismatchException(
          expected: expected,
          actual: fingerprints.identity,
        );
      }
      final builder = BytesBuilder(copy: false);
      var length = 0;
      await for (final chunk in response.timeout(timeout)) {
        length += chunk.length;
        if (length > _maximumIconBytes) {
          throw const ApiException('The app icon is too large.');
        }
        builder.add(chunk);
      }
      final bytes = builder.takeBytes();
      if (bytes.isEmpty) {
        throw const ApiException('The app icon is empty.');
      }
      return bytes;
    } on IdentityMismatchException {
      rethrow;
    } on ApiException {
      rethrow;
    } on HandshakeException catch (_) {
      final expected = trustedIdentity;
      if (expected != null) {
        throw IdentityMismatchException(expected: expected);
      }
      throw const ApiException(
          'Unable to establish a secure connection to the Windows PC.');
    } on TimeoutException catch (_) {
      throw const ApiException('The app icon request timed out.');
    } on SocketException catch (_) {
      throw const ApiException('Unable to download the app icon.');
    }
  }

  @override
  Future<void> launchApp(String appId) async {
    if (!RegExp(r'^[a-z0-9][a-z0-9_-]{0,31}$').hasMatch(appId)) {
      throw const FormatException('Configured app ID is invalid.');
    }
    await _send(
      'POST',
      '/apps/${Uri.encodeComponent(appId)}/launch',
      body: const <String, Object?>{},
      authenticated: true,
    );
  }

  @override
  Future<void> sendAction(String action) => _sendCommand(
        '/action',
        <String, Object?>{'action': action},
      );

  @override
  Future<void> sendMouseMove(double dx, double dy) => _sendCommand(
        '/mouse',
        <String, Object?>{'type': 'move', 'dx': dx, 'dy': dy},
      );

  @override
  Future<void> sendMouseClick({String button = 'left'}) => _sendCommand(
        '/mouse',
        <String, Object?>{'type': 'click', 'button': button},
      );

  @override
  Future<void> sendMouseDoubleClick() => _sendCommand(
        '/mouse',
        const <String, Object?>{'type': 'double'},
      );

  @override
  Future<void> sendMouseWheel(double delta) => _sendCommand(
        '/mouse',
        <String, Object?>{'type': 'wheel', 'delta': delta},
      );

  @override
  Future<void> sendText(String text) {
    if (text.length > 2000) {
      throw const FormatException('Text must not exceed 2000 characters.');
    }
    return _sendCommand('/text', <String, Object?>{'text': text});
  }

  @override
  Future<void> sendPowerAction(String action) => _sendCommand(
        '/power',
        <String, Object?>{'action': action},
      );

  Future<void> _sendCommand(String path, Map<String, Object?> body) async {
    await _send('POST', path, body: body, authenticated: true);
  }

  Future<_VerifiedResponse> _send(
    String method,
    String path, {
    Map<String, Object?>? body,
    bool authenticated = false,
  }) async {
    try {
      final request = await _httpClient
          .openUrl(method, endpoint.apiUri(path))
          .timeout(timeout);
      request.headers.set(HttpHeaders.acceptHeader, ContentType.json.mimeType);
      if (authenticated) {
        final token = credential;
        if (token == null || token.isEmpty) {
          throw const UnauthorizedException(
              'No saved credential is available.');
        }
        request.headers.set(HttpHeaders.authorizationHeader, 'Bearer $token');
      }
      if (body != null) {
        final payload = utf8.encode(jsonEncode(body));
        request.headers.contentType = ContentType.json;
        request.contentLength = payload.length;
        request.add(payload);
      }
      final response = await request.close().timeout(timeout);
      final certificate = response.certificate;
      if (certificate == null) {
        throw const ApiException(
            'The Windows PC did not provide a TLS certificate.');
      }
      final fingerprints = _fingerprintsFor(certificate);
      final text = await utf8.decoder.bind(response).join().timeout(timeout);
      final decoded =
          text.isEmpty ? const <String, Object?>{} : jsonDecode(text);
      final responseBody = decoded is Map<String, Object?>
          ? decoded
          : throw const ApiException(
              'The Windows PC returned an invalid response.');
      if (response.statusCode == HttpStatus.unauthorized) {
        throw UnauthorizedException(_errorMessage(responseBody));
      }
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw ApiException(
          _errorMessage(responseBody),
          statusCode: response.statusCode,
        );
      }
      return _VerifiedResponse(responseBody, fingerprints);
    } on IdentityMismatchException {
      rethrow;
    } on ApiException {
      rethrow;
    } on HandshakeException catch (_) {
      final expected = trustedIdentity;
      if (expected != null) {
        throw IdentityMismatchException(expected: expected);
      }
      throw const ApiException(
          'Unable to establish a secure connection to the Windows PC.');
    } on TimeoutException catch (_) {
      throw const ApiException('The Windows PC did not respond in time.');
    } on SocketException catch (_) {
      throw const ApiException(
          'Unable to reach the Windows PC on the local network.');
    } on FormatException catch (_) {
      throw const ApiException('The Windows PC returned an invalid response.');
    }
  }

  @override
  void close() => _httpClient.close(force: true);

  CertificateFingerprints _fingerprintsFor(X509Certificate certificate) {
    final pem = certificate.pem;
    final cached = _cachedFingerprints;
    if (_cachedCertificatePem == pem && cached != null) {
      return cached;
    }
    final fingerprints = _verifier.inspect(certificate.der);
    _cachedCertificatePem = pem;
    _cachedFingerprints = fingerprints;
    return fingerprints;
  }

  void _verifyServer(String serverId, int apiVersion) {
    if (apiVersion != 1) {
      throw ApiException('Unsupported API version: $apiVersion.');
    }
    final expected = expectedServerId;
    if (expected != null && expected != serverId) {
      throw const ApiException(
        'The Windows PC server ID changed. Pair again to continue.',
      );
    }
  }

  static String _errorMessage(Map<String, Object?> body) {
    final error = body['error'];
    return error is String && error.isNotEmpty
        ? error
        : 'The Windows PC rejected the request.';
  }

  static bool _sameFingerprint(String left, String right) =>
      left.toLowerCase() == right.toLowerCase();
}

class _VerifiedResponse {
  const _VerifiedResponse(this.body, this.fingerprints);

  final Map<String, Object?> body;
  final CertificateFingerprints fingerprints;
}
