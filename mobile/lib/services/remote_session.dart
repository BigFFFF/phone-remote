import '../models/api_models.dart';
import '../models/device.dart';
import '../models/server_endpoint.dart';
import '../repositories/device_repository.dart';
import 'api_client.dart';

abstract interface class RemoteSession {
  Device get device;

  ServerStatus get status;

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

abstract interface class RemoteSessionFactory {
  Future<RemoteSession> connect(Device device);
}

class RealRemoteSessionFactory implements RemoteSessionFactory {
  const RealRemoteSessionFactory({
    required DeviceRepository deviceRepository,
    required ApiClientFactory apiClientFactory,
  })  : _deviceRepository = deviceRepository,
        _apiClientFactory = apiClientFactory;

  final DeviceRepository _deviceRepository;
  final ApiClientFactory _apiClientFactory;

  @override
  Future<RemoteSession> connect(Device device) async {
    if (!device.isPaired) {
      throw const UnauthorizedException('Pair with this PC before connecting.');
    }
    final credential = await _deviceRepository.readCredential(device);
    if (credential == null || credential.isEmpty) {
      throw const UnauthorizedException(
        'The saved credential is missing. Pair with this PC again.',
      );
    }
    final client = _apiClientFactory.create(
      ServerEndpoint(host: device.host, port: device.port),
      trustedIdentity: device.serverIdentity,
      expectedServerId: device.serverId,
      credential: credential,
    );
    try {
      await client.getInfo();
      final status = await client.getStatus();
      WakeTarget? wakeTarget;
      for (final target in status.wakeTargets) {
        if (target.address == device.host ||
            target.address == device.lastIpv4) {
          wakeTarget = target;
          break;
        }
      }
      if (wakeTarget == null && status.wakeTargets.isNotEmpty) {
        wakeTarget = status.wakeTargets.first;
      }
      final connectedDevice = device.copyWith(
        name: status.name,
        lastIpv4: status.addresses.isEmpty ? null : status.addresses.first,
        mac: wakeTarget?.mac,
        broadcastAddress: wakeTarget?.broadcast,
        lastSeen: DateTime.now().toUtc(),
      );
      return ApiRemoteSession(
        device: connectedDevice,
        status: status,
        client: client,
      );
    } catch (_) {
      client.close();
      rethrow;
    }
  }
}

class ApiRemoteSession implements RemoteSession {
  const ApiRemoteSession({
    required this.device,
    required this.status,
    required PhoneRemoteApiClient client,
  }) : _client = client;

  @override
  final Device device;

  @override
  final ServerStatus status;

  final PhoneRemoteApiClient _client;

  @override
  Future<List<ConfiguredApp>> getApps() => _client.getApps();

  @override
  Future<void> launchApp(String appId) => _client.launchApp(appId);

  @override
  Future<void> sendAction(String action) => _client.sendAction(action);

  @override
  Future<void> sendMouseMove(double dx, double dy) =>
      _client.sendMouseMove(dx, dy);

  @override
  Future<void> sendMouseClick({String button = 'left'}) =>
      _client.sendMouseClick(button: button);

  @override
  Future<void> sendMouseDoubleClick() => _client.sendMouseDoubleClick();

  @override
  Future<void> sendMouseWheel(double delta) => _client.sendMouseWheel(delta);

  @override
  Future<void> sendText(String text) => _client.sendText(text);

  @override
  Future<void> sendPowerAction(String action) =>
      _client.sendPowerAction(action);

  @override
  void close() => _client.close();
}
