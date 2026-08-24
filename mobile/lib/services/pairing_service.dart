import '../models/api_models.dart';
import '../models/device.dart';
import '../models/server_endpoint.dart';
import '../repositories/device_repository.dart';
import 'api_client.dart';

class PairingAttempt {
  const PairingAttempt({
    required this.endpoint,
    required this.server,
    required this.session,
  });

  final ServerEndpoint endpoint;
  final ServerInfo server;
  final PairingSession session;
}

class PairingService {
  const PairingService({
    required this._apiClientFactory,
    required this._deviceRepository,
  });

  final ApiClientFactory _apiClientFactory;
  final DeviceRepository _deviceRepository;

  Future<PairingAttempt> begin(ServerEndpoint endpoint) async {
    final probe = _apiClientFactory.create(endpoint);
    late final ServerInfo server;
    try {
      server = await probe.getInfo();
    } finally {
      probe.close();
    }

    final pinned = _apiClientFactory.create(
      endpoint,
      trustedIdentity: server.identityFingerprint,
      expectedServerId: server.serverId,
    );
    try {
      final verifiedServer = await pinned.getInfo();
      final session = await pinned.requestPairing();
      return PairingAttempt(
        endpoint: endpoint,
        server: verifiedServer,
        session: session,
      );
    } finally {
      pinned.close();
    }
  }

  Future<Device> complete({
    required PairingAttempt attempt,
    required String code,
    required String deviceName,
    required String platform,
  }) async {
    final normalizedCode = code.trim();
    final normalizedName = deviceName.trim();
    final normalizedPlatform = platform.trim();
    if (!RegExp(r'^[0-9]{6}$').hasMatch(normalizedCode)) {
      throw const FormatException('Enter the six-digit code shown on the PC.');
    }
    if (normalizedName.isEmpty || normalizedName.length > 120) {
      throw const FormatException(
          'Device name must be between 1 and 120 characters.');
    }
    if (normalizedPlatform.isEmpty || normalizedPlatform.length > 40) {
      throw const FormatException(
          'Platform name must be between 1 and 40 characters.');
    }

    final api = _apiClientFactory.create(
      attempt.endpoint,
      trustedIdentity: attempt.server.identityFingerprint,
      expectedServerId: attempt.server.serverId,
    );
    late final PairingResult result;
    try {
      result = await api.completePairing(
        sessionId: attempt.session.sessionId,
        code: normalizedCode,
        deviceName: normalizedName,
        platform: normalizedPlatform,
      );
    } finally {
      api.close();
    }
    if (result.serverId != attempt.server.serverId ||
        result.identityFingerprint != attempt.server.identityFingerprint) {
      throw IdentityMismatchException(
        expected: attempt.server.identityFingerprint,
        actual: result.identityFingerprint,
      );
    }

    final existing = await _deviceRepository.findByServerId(result.serverId);
    final credentialReference = 'phone_remote.credential.${result.clientId}';
    final device = Device(
      id: existing?.id ?? result.serverId,
      serverId: result.serverId,
      name: attempt.server.name,
      host: attempt.endpoint.host,
      port: attempt.endpoint.port,
      mac: existing?.mac,
      lastIpv4: existing?.lastIpv4,
      broadcastAddress: existing?.broadcastAddress,
      serverIdentity: result.identityFingerprint,
      certificateFingerprint: attempt.server.certificateFingerprint,
      clientId: result.clientId,
      credentialReference: credentialReference,
      lastSeen: DateTime.now().toUtc(),
      favorite: existing?.favorite ?? false,
    );
    await _deviceRepository.savePaired(device, result.credential);
    return device;
  }
}
