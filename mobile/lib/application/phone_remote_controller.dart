import 'dart:async';

import 'package:flutter/foundation.dart';

import '../models/api_models.dart';
import '../models/device.dart';
import '../models/server_endpoint.dart';
import '../repositories/device_repository.dart';
import '../services/api_client.dart';
import '../services/discovery_service.dart';
import '../services/pairing_service.dart';
import '../services/remote_session.dart';
import '../services/wake_service.dart';

enum RemoteConnectionPhase {
  disconnected,
  connecting,
  waking,
  connected,
  offline,
  unauthorized,
  identityMismatch,
}

class PhoneRemoteController extends ChangeNotifier {
  PhoneRemoteController({
    required this._deviceRepository,
    required this._discoveryService,
    required this._pairingService,
    required this._remoteSessionFactory,
    required this._wakeService,
    Future<void> Function(Duration duration)? delay,
  })  : _delay = delay ?? _defaultDelay;

  final DeviceRepository _deviceRepository;
  final DiscoveryService _discoveryService;
  final PairingService _pairingService;
  final RemoteSessionFactory _remoteSessionFactory;
  final WakeService _wakeService;
  final Future<void> Function(Duration duration) _delay;

  List<Device> _devices = const <Device>[];
  List<DiscoveredDevice> _discoveredDevices = const <DiscoveredDevice>[];
  List<ConfiguredApp> _apps = const <ConfiguredApp>[];
  bool _initialized = false;
  bool _searching = false;
  Device? _selectedDevice;
  RemoteSession? _session;
  RemoteConnectionPhase _connectionPhase = RemoteConnectionPhase.disconnected;
  String? _connectionError;
  int _connectionGeneration = 0;

  List<Device> get devices => _devices;
  List<DiscoveredDevice> get discoveredDevices => _discoveredDevices;
  List<ConfiguredApp> get apps => _apps;
  bool get initialized => _initialized;
  bool get searching => _searching;
  Device? get selectedDevice => _selectedDevice;
  RemoteConnectionPhase get connectionPhase => _connectionPhase;
  String? get connectionError => _connectionError;
  bool get connected => _connectionPhase == RemoteConnectionPhase.connected;
  ServerStatus? get serverStatus => _session?.status;

  Device? get preferredDevice {
    final selected = _selectedDevice;
    if (selected != null) {
      return selected;
    }
    if (_devices.isEmpty) {
      return null;
    }
    return _devices.firstWhere(
      (device) => device.favorite,
      orElse: () => _devices.first,
    );
  }

  Future<void> initialize() async {
    if (_initialized) {
      return;
    }
    await refreshDevices();
    _initialized = true;
    notifyListeners();
    final preferred = preferredDevice;
    if (preferred != null) {
      unawaited(connect(preferred));
    }
  }

  Future<void> refreshDevices() async {
    _devices = await _deviceRepository.getAll();
    final selected = _selectedDevice;
    if (selected != null) {
      for (final device in _devices) {
        if (device.id == selected.id) {
          _selectedDevice = device;
          break;
        }
      }
    }
    notifyListeners();
  }

  Future<void> discover() async {
    if (_searching) {
      return;
    }
    _searching = true;
    notifyListeners();
    try {
      _discoveredDevices = await _discoveryService.discover();
    } finally {
      _searching = false;
      notifyListeners();
    }
  }

  Future<PairingAttempt> beginPairing(ServerEndpoint endpoint) =>
      _pairingService.begin(endpoint);

  Future<Device> completePairing({
    required PairingAttempt attempt,
    required String code,
    required String deviceName,
    required String platform,
  }) async {
    final device = await _pairingService.complete(
      attempt: attempt,
      code: code,
      deviceName: deviceName,
      platform: platform,
    );
    await refreshDevices();
    unawaited(connect(device, autoWake: false));
    return device;
  }

  Future<void> connect(Device device, {bool autoWake = false}) async {
    final generation = ++_connectionGeneration;
    _session?.close();
    _session = null;
    _selectedDevice = device;
    _apps = const <ConfiguredApp>[];
    _connectionError = null;
    _connectionPhase = RemoteConnectionPhase.connecting;
    notifyListeners();

    try {
      await _connectOnce(device, generation);
      return;
    } on UnauthorizedException catch (error) {
      _failConnection(
          RemoteConnectionPhase.unauthorized, error.message, generation);
      return;
    } on IdentityMismatchException catch (error) {
      _failConnection(
        RemoteConnectionPhase.identityMismatch,
        error.message,
        generation,
      );
      return;
    } on ApiException catch (initialError) {
      if (!autoWake || !await _canWake(device, generation)) {
        _failConnection(
          RemoteConnectionPhase.offline,
          initialError.message,
          generation,
        );
        return;
      }
      try {
        _connectionPhase = RemoteConnectionPhase.waking;
        notifyListeners();
        await _wakeService.wake(device);
      } catch (error) {
        _failConnection(
          RemoteConnectionPhase.offline,
          'Unable to wake this PC: $error',
          generation,
        );
        return;
      }
      for (final wait in const <Duration>[
        Duration(seconds: 1),
        Duration(seconds: 2),
        Duration(seconds: 3),
        Duration(seconds: 5),
        Duration(seconds: 8),
        Duration(seconds: 12),
      ]) {
        if (generation != _connectionGeneration) {
          return;
        }
        await _delay(wait);
        if (generation != _connectionGeneration) {
          return;
        }
        _connectionPhase = RemoteConnectionPhase.connecting;
        notifyListeners();
        try {
          await _connectOnce(device, generation);
          return;
        } on UnauthorizedException catch (error) {
          _failConnection(
            RemoteConnectionPhase.unauthorized,
            error.message,
            generation,
          );
          return;
        } on IdentityMismatchException catch (error) {
          _failConnection(
            RemoteConnectionPhase.identityMismatch,
            error.message,
            generation,
          );
          return;
        } on ApiException {
          // Keep retrying while the Windows PC wakes and joins the LAN.
        }
      }
      _failConnection(
        RemoteConnectionPhase.offline,
        'The wake packet was sent, but the PC did not come online.',
        generation,
      );
    } catch (_) {
      _failConnection(
        RemoteConnectionPhase.offline,
        'Unable to connect to this PC.',
        generation,
      );
    }
  }

  Future<void> _connectOnce(Device device, int generation) async {
    final session = await _remoteSessionFactory.connect(device);
    if (generation != _connectionGeneration) {
      session.close();
      return;
    }
    _session = session;
    _selectedDevice = session.device;
    await _deviceRepository.save(session.device);
    if (generation != _connectionGeneration || !identical(_session, session)) {
      session.close();
      return;
    }
    _connectionPhase = RemoteConnectionPhase.connected;
    _connectionError = session.status.configOk
        ? null
        : session.status.configError ?? 'The PC configuration needs attention.';
    notifyListeners();
    var apps = const <ConfiguredApp>[];
    String? appsError;
    try {
      apps = await session.getApps();
    } on IdentityMismatchException catch (error) {
      session.close();
      _failConnection(
        RemoteConnectionPhase.identityMismatch,
        error.message,
        generation,
      );
      return;
    } on ApiException catch (error) {
      appsError = 'Connected, but apps could not be loaded: ${error.message}';
    } catch (_) {
      appsError = 'Connected, but the PC returned an invalid app list.';
    }
    if (generation != _connectionGeneration || !identical(_session, session)) {
      return;
    }
    _apps = apps;
    if (appsError != null) {
      _connectionError = appsError;
    }
    await refreshDevices();
    if (generation != _connectionGeneration || !identical(_session, session)) {
      return;
    }
    notifyListeners();
  }

  Future<bool> _canWake(Device device, int generation) async {
    final capability = await _wakeService.capability(device);
    return generation == _connectionGeneration &&
        capability.availability == WakeAvailability.available;
  }

  void _failConnection(
    RemoteConnectionPhase phase,
    String message,
    int generation,
  ) {
    if (generation != _connectionGeneration) {
      return;
    }
    _session?.close();
    _session = null;
    _connectionPhase = phase;
    _connectionError = message;
    notifyListeners();
  }

  Future<void> reconnect() async {
    final device = preferredDevice;
    if (device != null) {
      await connect(device);
    }
  }

  Future<void> wakeAndConnect() async {
    final device = preferredDevice;
    if (device == null) {
      throw const ApiException('Add a PC before using Wake on LAN.');
    }
    final capability = await _wakeService.capability(device);
    if (capability.availability != WakeAvailability.available) {
      throw ApiException(
        capability.unavailableReason ??
            'Wake on LAN is unavailable for this PC.',
      );
    }
    await connect(device, autoWake: true);
    if (!connected) {
      throw ApiException(
        _connectionError ?? 'The PC did not come online after Wake on LAN.',
      );
    }
  }

  Future<void> sendAction(String action) =>
      _run((session) => session.sendAction(action));

  Future<void> sendMouseMove(double dx, double dy) =>
      _run((session) => session.sendMouseMove(dx, dy));

  Future<void> sendMouseClick({String button = 'left'}) =>
      _run((session) => session.sendMouseClick(button: button));

  Future<void> sendMouseDoubleClick() =>
      _run((session) => session.sendMouseDoubleClick());

  Future<void> sendMouseWheel(double delta) =>
      _run((session) => session.sendMouseWheel(delta));

  Future<void> sendText(String text) =>
      _run((session) => session.sendText(text));

  Future<void> sendPowerAction(String action) async {
    final activeSession = _session;
    await _run((session) => session.sendPowerAction(action));
    if ((action == 'sleep' || action == 'hibernate') &&
        identical(_session, activeSession)) {
      _connectionGeneration += 1;
      activeSession?.close();
      _session = null;
      _apps = const <ConfiguredApp>[];
      _connectionPhase = RemoteConnectionPhase.offline;
      _connectionError = action == 'sleep'
          ? 'The PC is in standby. Use Wake on LAN in Settings to wake it.'
          : 'The PC is hibernating. Wake on LAN may be unavailable.';
      notifyListeners();
    }
  }

  Future<void> launchApp(String appId) =>
      _run((session) => session.launchApp(appId));

  Future<void> _run(
      Future<void> Function(RemoteSession session) operation) async {
    final session = _session;
    if (session == null || !connected) {
      throw ApiException(_connectionError ?? 'Connect to a PC first.');
    }
    try {
      await operation(session);
    } on UnauthorizedException catch (error) {
      _connectionPhase = RemoteConnectionPhase.unauthorized;
      _connectionError = error.message;
      session.close();
      _session = null;
      notifyListeners();
      rethrow;
    } on IdentityMismatchException catch (error) {
      _connectionPhase = RemoteConnectionPhase.identityMismatch;
      _connectionError = error.message;
      session.close();
      _session = null;
      notifyListeners();
      rethrow;
    } on ApiException catch (error) {
      _connectionError = error.message;
      if (error.statusCode == null) {
        _connectionPhase = RemoteConnectionPhase.offline;
        session.close();
        _session = null;
      }
      notifyListeners();
      rethrow;
    }
  }

  Future<void> toggleFavorite(Device device) async {
    final makingFavorite = !device.favorite;
    if (makingFavorite && _selectedDevice?.id != device.id) {
      _connectionGeneration += 1;
      _session?.close();
      _session = null;
    }
    for (final item in _devices) {
      if (item.favorite && item.id != device.id) {
        await _deviceRepository.save(item.copyWith(favorite: false));
      }
    }
    final updated = device.copyWith(favorite: makingFavorite);
    await _deviceRepository.save(updated);
    if (makingFavorite) {
      _selectedDevice = updated;
    }
    await refreshDevices();
    if (makingFavorite) {
      await connect(updated, autoWake: false);
    }
  }

  Future<void> remove(Device device) async {
    if (_selectedDevice?.id == device.id) {
      _connectionGeneration += 1;
      _session?.close();
      _session = null;
      _selectedDevice = null;
      _apps = const <ConfiguredApp>[];
      _connectionPhase = RemoteConnectionPhase.disconnected;
      _connectionError = null;
    }
    await _deviceRepository.remove(device);
    await refreshDevices();
  }

  @override
  void dispose() {
    _connectionGeneration += 1;
    _session?.close();
    super.dispose();
  }
}

Future<void> _defaultDelay(Duration duration) => Future<void>.delayed(duration);
