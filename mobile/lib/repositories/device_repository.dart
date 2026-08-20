import 'dart:convert';

import '../data/storage.dart';
import '../models/device.dart';

abstract interface class DeviceRepository {
  Future<List<Device>> getAll();

  Future<Device?> findByServerId(String serverId);

  Future<void> savePaired(Device device, String credential);

  Future<void> save(Device device);

  Future<String?> readCredential(Device device);

  Future<void> remove(Device device);
}

class RealDeviceRepository implements DeviceRepository {
  RealDeviceRepository({
    required MetadataStorage metadataStorage,
    required CredentialStorage credentialStorage,
  })  : _metadataStorage = metadataStorage,
        _credentialStorage = credentialStorage;

  static const _devicesKey = 'phone_remote.devices.v1';

  final MetadataStorage _metadataStorage;
  final CredentialStorage _credentialStorage;

  @override
  Future<List<Device>> getAll() async {
    final encoded = await _metadataStorage.read(_devicesKey);
    if (encoded == null) {
      return <Device>[];
    }
    final value = jsonDecode(encoded);
    if (value is! List<Object?>) {
      throw const FormatException('Saved devices must be a JSON array.');
    }
    final devices = value.map((item) {
      if (item is! Map<String, Object?>) {
        throw const FormatException('Saved device entry must be an object.');
      }
      return Device.fromJson(item);
    }).toList();
    devices.sort(_compareDevices);
    return List<Device>.unmodifiable(devices);
  }

  @override
  Future<Device?> findByServerId(String serverId) async {
    for (final device in await getAll()) {
      if (device.serverId == serverId) {
        return device;
      }
    }
    return null;
  }

  @override
  Future<void> savePaired(Device device, String credential) async {
    final reference = device.credentialReference;
    if (!device.isPaired || reference == null || credential.isEmpty) {
      throw ArgumentError(
          'A paired device and non-empty credential are required.');
    }
    await _credentialStorage.write(reference, credential);
    await save(device);
  }

  @override
  Future<void> save(Device device) async {
    final devices = (await getAll()).toList();
    final existingIndex = devices.indexWhere(
      (candidate) =>
          candidate.id == device.id || candidate.serverId == device.serverId,
    );
    if (existingIndex == -1) {
      devices.add(device);
    } else {
      final existing = devices[existingIndex];
      devices[existingIndex] = device.copyWith(
        id: existing.id,
      );
    }
    devices.sort(_compareDevices);
    await _metadataStorage.write(
      _devicesKey,
      jsonEncode(devices.map((item) => item.toJson()).toList()),
    );
  }

  @override
  Future<String?> readCredential(Device device) async {
    final reference = device.credentialReference;
    return reference == null ? null : _credentialStorage.read(reference);
  }

  @override
  Future<void> remove(Device device) async {
    final devices = (await getAll())
        .where((candidate) => candidate.id != device.id)
        .toList();
    await _metadataStorage.write(
      _devicesKey,
      jsonEncode(devices.map((item) => item.toJson()).toList()),
    );
    final reference = device.credentialReference;
    if (reference != null) {
      await _credentialStorage.delete(reference);
    }
  }

  static int _compareDevices(Device left, Device right) {
    if (left.favorite != right.favorite) {
      return left.favorite ? -1 : 1;
    }
    final leftSeen = left.lastSeen;
    final rightSeen = right.lastSeen;
    if (leftSeen != null || rightSeen != null) {
      if (leftSeen == null) {
        return 1;
      }
      if (rightSeen == null) {
        return -1;
      }
      final seenOrder = rightSeen.compareTo(leftSeen);
      if (seenOrder != 0) {
        return seenOrder;
      }
    }
    return left.name.toLowerCase().compareTo(right.name.toLowerCase());
  }
}

class DemoDeviceRepository implements DeviceRepository {
  DemoDeviceRepository()
      : _devices = <Device>[
          const Device(
            id: 'demo-living-room',
            serverId: 'demo-living-room',
            name: 'Living Room PC',
            host: 'demo.local',
            serverIdentity:
                'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd',
            clientId: 'demo-client',
            credentialReference: 'demo-credential',
            favorite: true,
          ),
        ];

  final List<Device> _devices;

  @override
  Future<List<Device>> getAll() async => List<Device>.unmodifiable(_devices);

  @override
  Future<Device?> findByServerId(String serverId) async {
    for (final device in _devices) {
      if (device.serverId == serverId) {
        return device;
      }
    }
    return null;
  }

  @override
  Future<void> savePaired(Device device, String credential) => save(device);

  @override
  Future<void> save(Device device) async {
    final index =
        _devices.indexWhere((item) => item.serverId == device.serverId);
    if (index == -1) {
      _devices.add(device);
    } else {
      _devices[index] = device;
    }
  }

  @override
  Future<String?> readCredential(Device device) async => 'demo';

  @override
  Future<void> remove(Device device) async => _devices.remove(device);
}
