import 'dart:async';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:phone_remote/application/phone_remote_controller.dart';
import 'package:phone_remote/models/api_models.dart';
import 'package:phone_remote/models/device.dart';
import 'package:phone_remote/repositories/device_repository.dart';
import 'package:phone_remote/services/api_client.dart';
import 'package:phone_remote/services/discovery_service.dart';
import 'package:phone_remote/services/pairing_service.dart';
import 'package:phone_remote/services/remote_session.dart';
import 'package:phone_remote/services/wake_service.dart';

import 'support/fake_api.dart';
import 'support/memory_storage.dart';

void main() {
  test('controller chooses and changes a single favorite PC', () async {
    final repository = RealDeviceRepository(
      metadataStorage: MemoryMetadataStorage(),
      credentialStorage: MemoryCredentialStorage(),
    );
    final first = _device('first', favorite: true);
    final second = _device('second');
    await repository.savePaired(first, 'first-secret');
    await repository.savePaired(second, 'second-secret');
    final controller = _controller(repository);
    await controller.initialize();

    expect(controller.preferredDevice?.serverId, 'first');
    await controller.toggleFavorite(second);

    expect(controller.preferredDevice?.serverId, 'second');
    expect(controller.devices.where((device) => device.favorite), hasLength(1));
  });

  test('controller publishes merged discovery results', () async {
    final repository = RealDeviceRepository(
      metadataStorage: MemoryMetadataStorage(),
      credentialStorage: MemoryCredentialStorage(),
    );
    final controller = _controller(
      repository,
      discovery: const _FakeDiscoveryService(),
    );
    await controller.initialize();

    await controller.discover();

    expect(controller.searching, isFalse);
    expect(controller.discoveredDevices.single.serverId, 'discovered-1');
  });

  test(
    'ordinary connect never wakes a trusted offline PC automatically',
    () async {
      final repository = RealDeviceRepository(
        metadataStorage: MemoryMetadataStorage(),
        credentialStorage: MemoryCredentialStorage(),
      );
      final device = _device('sleeping').copyWith(mac: '00:11:22:33:44:55');
      await repository.savePaired(device, 'secret');
      final sessions = _FlakySessionFactory();
      final wake = _RecordingWakeService();
      final controller = PhoneRemoteController(
        deviceRepository: repository,
        discoveryService: const _FakeDiscoveryService(),
        pairingService: PairingService(
          apiClientFactory: _apiFactory(),
          deviceRepository: repository,
        ),
        remoteSessionFactory: sessions,
        wakeService: wake,
      );

      await controller.connect(device);

      expect(controller.connectionPhase, RemoteConnectionPhase.offline);
      expect(sessions.attempts, 1);
      expect(wake.sent, 0);
    },
  );

  test('manual Wake on LAN retries a trusted offline PC', () async {
    final repository = RealDeviceRepository(
      metadataStorage: MemoryMetadataStorage(),
      credentialStorage: MemoryCredentialStorage(),
    );
    final device = _device('sleeping').copyWith(mac: '00:11:22:33:44:55');
    await repository.savePaired(device, 'secret');
    final sessions = _FlakySessionFactory(failuresBeforeSuccess: 2);
    final wake = _RecordingWakeService();
    final waits = <Duration>[];
    final apiFactory = _apiFactory();
    final controller = PhoneRemoteController(
      deviceRepository: repository,
      discoveryService: const _FakeDiscoveryService(),
      pairingService: PairingService(
        apiClientFactory: apiFactory,
        deviceRepository: repository,
      ),
      remoteSessionFactory: sessions,
      wakeService: wake,
      delay: (duration) async => waits.add(duration),
    );

    await controller.initialize();
    await controller.wakeAndConnect();

    expect(controller.connectionPhase, RemoteConnectionPhase.connected);
    expect(sessions.attempts, 3);
    expect(wake.sent, 1);
    expect(waits, <Duration>[const Duration(seconds: 1)]);
  });

  test(
    'sleep marks the session offline and exposes manual Wake on LAN guidance',
    () async {
      final repository = RealDeviceRepository(
        metadataStorage: MemoryMetadataStorage(),
        credentialStorage: MemoryCredentialStorage(),
      );
      final device = _device('sleeping').copyWith(mac: '00:11:22:33:44:55');
      await repository.savePaired(device, 'secret');
      final controller = PhoneRemoteController(
        deviceRepository: repository,
        discoveryService: const _FakeDiscoveryService(),
        pairingService: PairingService(
          apiClientFactory: _apiFactory(),
          deviceRepository: repository,
        ),
        remoteSessionFactory: _AlwaysConnectedSessionFactory(),
        wakeService: _RecordingWakeService(),
      );
      await controller.connect(device);

      await controller.sendPowerAction('sleep');

      expect(controller.connectionPhase, RemoteConnectionPhase.offline);
      expect(controller.connectionError, contains('Wake on LAN'));
    },
  );

  test(
    'transient pointer failures do not immediately close the session',
    () async {
      final repository = RealDeviceRepository(
        metadataStorage: MemoryMetadataStorage(),
        credentialStorage: MemoryCredentialStorage(),
      );
      final device = _device('pointer');
      await repository.savePaired(device, 'secret');
      final session = _PointerFailureSession(device, remainingFailures: 2);
      final controller = PhoneRemoteController(
        deviceRepository: repository,
        discoveryService: const _FakeDiscoveryService(),
        pairingService: PairingService(
          apiClientFactory: _apiFactory(),
          deviceRepository: repository,
        ),
        remoteSessionFactory: _SingleSessionFactory(session),
        wakeService: const UnavailableWakeService('Unavailable in tests.'),
      );
      await controller.connect(device);

      await expectLater(
        controller.sendMouseMove(1, 1),
        throwsA(isA<ApiException>()),
      );
      await expectLater(
        controller.sendMouseMove(1, 1),
        throwsA(isA<ApiException>()),
      );
      expect(controller.connected, isTrue);
      expect(session.closed, isFalse);

      await controller.sendMouseMove(1, 1);
      session.remainingFailures = 3;
      await expectLater(
        controller.sendMouseMove(1, 1),
        throwsA(isA<ApiException>()),
      );
      await expectLater(
        controller.sendMouseMove(1, 1),
        throwsA(isA<ApiException>()),
      );
      expect(controller.connected, isTrue);
      await expectLater(
        controller.sendMouseMove(1, 1),
        throwsA(isA<ApiException>()),
      );
      expect(controller.connectionPhase, RemoteConnectionPhase.offline);
      expect(session.closed, isTrue);
    },
  );

  test('progressive app icons notify only the app-list listener', () async {
    final repository = RealDeviceRepository(
      metadataStorage: MemoryMetadataStorage(),
      credentialStorage: MemoryCredentialStorage(),
    );
    final device = _device('apps');
    await repository.savePaired(device, 'secret');
    final session = _ProgressiveAppsSession(device);
    final controller = PhoneRemoteController(
      deviceRepository: repository,
      discoveryService: const _FakeDiscoveryService(),
      pairingService: PairingService(
        apiClientFactory: _apiFactory(),
        deviceRepository: repository,
      ),
      remoteSessionFactory: _SingleSessionFactory(session),
      wakeService: const UnavailableWakeService('Unavailable in tests.'),
    );
    await controller.connect(device);
    var controllerChanges = 0;
    var appChanges = 0;
    controller.addListener(() => controllerChanges += 1);
    controller.appsListenable.addListener(() => appChanges += 1);

    session.publishIcon();
    await Future<void>.delayed(Duration.zero);

    expect(controllerChanges, 0);
    expect(appChanges, 1);
    expect(controller.apps.single.iconBytes, isNotNull);
  });

  test('an old wake retry cannot overwrite a newer PC connection', () async {
    final repository = RealDeviceRepository(
      metadataStorage: MemoryMetadataStorage(),
      credentialStorage: MemoryCredentialStorage(),
    );
    final first = _device('first').copyWith(mac: '00:11:22:33:44:55');
    final second = _device('second');
    await repository.savePaired(first, 'first-secret');
    await repository.savePaired(second, 'second-secret');
    final delayStarted = Completer<void>();
    final resumeWakeRetry = Completer<void>();
    final controller = PhoneRemoteController(
      deviceRepository: repository,
      discoveryService: const _FakeDiscoveryService(),
      pairingService: PairingService(
        apiClientFactory: _apiFactory(),
        deviceRepository: repository,
      ),
      remoteSessionFactory: _SwitchingSessionFactory(),
      wakeService: _RecordingWakeService(),
      delay: (_) {
        if (!delayStarted.isCompleted) {
          delayStarted.complete();
        }
        return resumeWakeRetry.future;
      },
    );

    final firstConnection = controller.connect(first, autoWake: true);
    await delayStarted.future;
    await controller.connect(second, autoWake: false);
    expect(controller.connectionPhase, RemoteConnectionPhase.connected);
    expect(controller.selectedDevice?.serverId, 'second');

    resumeWakeRetry.complete();
    await firstConnection;

    expect(controller.connectionPhase, RemoteConnectionPhase.connected);
    expect(controller.selectedDevice?.serverId, 'second');
  });

  test('an old app request cannot overwrite the newer PC app list', () async {
    final repository = RealDeviceRepository(
      metadataStorage: MemoryMetadataStorage(),
      credentialStorage: MemoryCredentialStorage(),
    );
    final first = _device('first');
    final second = _device('second');
    await repository.savePaired(first, 'first-secret');
    await repository.savePaired(second, 'second-secret');
    final oldAppsStarted = Completer<void>();
    final oldApps = Completer<List<ConfiguredApp>>();
    final controller = PhoneRemoteController(
      deviceRepository: repository,
      discoveryService: const _FakeDiscoveryService(),
      pairingService: PairingService(
        apiClientFactory: _apiFactory(),
        deviceRepository: repository,
      ),
      remoteSessionFactory: _OverlappingAppsSessionFactory(
        oldAppsStarted,
        oldApps,
      ),
      wakeService: const UnavailableWakeService('Unavailable in tests.'),
    );

    final firstConnection = controller.connect(first, autoWake: false);
    await oldAppsStarted.future;
    await firstConnection.timeout(const Duration(seconds: 1));
    expect(controller.connectionPhase, RemoteConnectionPhase.connected);
    await controller.connect(second, autoWake: false);
    expect(controller.apps.single.id, 'second-app');

    oldApps.complete(const <ConfiguredApp>[
      ConfiguredApp(
        id: 'first-app',
        name: 'First App',
        available: true,
        icon: '/first.png',
      ),
    ]);
    await firstConnection;

    expect(controller.apps.single.id, 'second-app');
    expect(controller.selectedDevice?.serverId, 'second');
  });
}

PhoneRemoteController _controller(
  DeviceRepository repository, {
  DiscoveryService discovery = const _FakeDiscoveryService(),
}) {
  final factory = _apiFactory();
  return PhoneRemoteController(
    deviceRepository: repository,
    discoveryService: discovery,
    pairingService: PairingService(
      apiClientFactory: factory,
      deviceRepository: repository,
    ),
    remoteSessionFactory: RealRemoteSessionFactory(
      deviceRepository: repository,
      apiClientFactory: factory,
    ),
    wakeService: const UnavailableWakeService('Unavailable in tests.'),
  );
}

FakeApiClientFactory _apiFactory() => FakeApiClientFactory(
  info: ServerInfo(
    serverId: 'server',
    name: 'PC',
    version: '1.0.0',
    apiVersion: 1,
    pairing: true,
    identityFingerprint: 'a' * 64,
    certificateFingerprint: 'b' * 64,
  ),
  session: const PairingSession(sessionId: 'session', expiresIn: 300),
  result: PairingResult(
    clientId: 'client',
    credential: 'secret',
    serverId: 'server',
    identityFingerprint: 'a' * 64,
  ),
);

Device _device(String serverId, {bool favorite = false}) {
  return Device(
    id: serverId,
    serverId: serverId,
    name: '$serverId PC',
    host: '192.168.1.20',
    serverIdentity: 'a' * 64,
    clientId: '$serverId-client',
    credentialReference: 'credential.$serverId',
    favorite: favorite,
  );
}

class _FakeDiscoveryService implements DiscoveryService {
  const _FakeDiscoveryService();

  @override
  Future<List<DiscoveredDevice>> discover({
    Duration timeout = const Duration(seconds: 5),
  }) async {
    return const <DiscoveredDevice>[
      DiscoveredDevice(
        serverId: 'discovered-1',
        name: 'Living Room PC',
        host: '192.168.1.30',
        port: 8765,
        apiVersion: 1,
        tls: true,
      ),
    ];
  }
}

class _FlakySessionFactory implements RemoteSessionFactory {
  _FlakySessionFactory({this.failuresBeforeSuccess = 1});

  final int failuresBeforeSuccess;
  int attempts = 0;

  @override
  Future<RemoteSession> connect(Device device) async {
    attempts += 1;
    if (attempts <= failuresBeforeSuccess) {
      throw const ApiException('PC is offline.');
    }
    return _TestRemoteSession(device);
  }
}

class _AlwaysConnectedSessionFactory implements RemoteSessionFactory {
  @override
  Future<RemoteSession> connect(Device device) async =>
      _TestRemoteSession(device);
}

class _SingleSessionFactory implements RemoteSessionFactory {
  const _SingleSessionFactory(this.session);

  final RemoteSession session;

  @override
  Future<RemoteSession> connect(Device device) async => session;
}

class _SwitchingSessionFactory implements RemoteSessionFactory {
  var _firstAttempts = 0;

  @override
  Future<RemoteSession> connect(Device device) async {
    if (device.serverId == 'first' && _firstAttempts++ == 0) {
      throw const ApiException('PC is offline.');
    }
    return _TestRemoteSession(device);
  }
}

class _OverlappingAppsSessionFactory implements RemoteSessionFactory {
  _OverlappingAppsSessionFactory(this.oldAppsStarted, this.oldApps);

  final Completer<void> oldAppsStarted;
  final Completer<List<ConfiguredApp>> oldApps;

  @override
  Future<RemoteSession> connect(Device device) async {
    if (device.serverId == 'first') {
      return _BlockingAppsSession(device, oldAppsStarted, oldApps);
    }
    return _ConfiguredAppsSession(device, const <ConfiguredApp>[
      ConfiguredApp(
        id: 'second-app',
        name: 'Second App',
        available: true,
        icon: '/second.png',
      ),
    ]);
  }
}

class _BlockingAppsSession extends _TestRemoteSession {
  _BlockingAppsSession(super.device, this.started, this.result);

  final Completer<void> started;
  final Completer<List<ConfiguredApp>> result;

  @override
  Future<List<ConfiguredApp>> getApps({AppsUpdateHandler? onUpdate}) {
    if (!started.isCompleted) {
      started.complete();
    }
    return result.future;
  }
}

class _ConfiguredAppsSession extends _TestRemoteSession {
  _ConfiguredAppsSession(super.device, this.configuredApps);

  final List<ConfiguredApp> configuredApps;

  @override
  Future<List<ConfiguredApp>> getApps({AppsUpdateHandler? onUpdate}) async {
    onUpdate?.call(configuredApps);
    return configuredApps;
  }
}

class _ProgressiveAppsSession extends _TestRemoteSession {
  _ProgressiveAppsSession(super.device);

  static const _metadata = <ConfiguredApp>[
    ConfiguredApp(
      id: 'browser',
      name: 'Browser',
      available: true,
      icon: '/browser.png',
    ),
  ];
  final Completer<List<ConfiguredApp>> _result =
      Completer<List<ConfiguredApp>>();
  AppsUpdateHandler? _onUpdate;

  @override
  Future<List<ConfiguredApp>> getApps({AppsUpdateHandler? onUpdate}) {
    _onUpdate = onUpdate;
    onUpdate?.call(_metadata);
    return _result.future;
  }

  void publishIcon() {
    final apps = <ConfiguredApp>[
      _metadata.single.withIconBytes(Uint8List.fromList(<int>[1, 2, 3])),
    ];
    _onUpdate?.call(apps);
    _result.complete(apps);
  }
}

class _PointerFailureSession extends _TestRemoteSession {
  _PointerFailureSession(super.device, {required this.remainingFailures});

  int remainingFailures;
  bool closed = false;

  @override
  Future<void> sendMouseMove(double dx, double dy) async {
    if (remainingFailures > 0) {
      remainingFailures -= 1;
      throw const ApiException('Temporary network failure.');
    }
  }

  @override
  void close() => closed = true;
}

class _TestRemoteSession implements RemoteSession {
  _TestRemoteSession(this.device);

  @override
  final Device device;

  @override
  ServerStatus get status => ServerStatus(
    serverId: device.serverId,
    name: device.name,
    version: '1.0.0',
    apiVersion: 1,
    addresses: const <String>['192.168.1.20'],
    port: 8765,
    configOk: true,
  );

  @override
  void close() {}

  @override
  Future<List<ConfiguredApp>> getApps({AppsUpdateHandler? onUpdate}) async {
    const apps = <ConfiguredApp>[];
    onUpdate?.call(apps);
    return apps;
  }

  @override
  Future<void> launchApp(String appId) async {}

  @override
  Future<void> sendAction(String action) async {}

  @override
  Future<void> sendMouseClick({String button = 'left'}) async {}

  @override
  Future<void> sendMouseDoubleClick() async {}

  @override
  Future<void> sendMouseMove(double dx, double dy) async {}

  @override
  Future<void> sendMouseWheel(double delta) async {}

  @override
  Future<void> sendPowerAction(String action) async {}

  @override
  Future<void> sendText(String text) async {}
}

class _RecordingWakeService implements WakeService {
  int sent = 0;

  @override
  Future<WakeCapability> capability(Device device) async =>
      const WakeCapability.available();

  @override
  Future<void> wake(Device device) async {
    sent += 1;
  }
}
