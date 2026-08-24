import 'dart:async';
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
    required this._metadataStorage,
    required this._credentialStorage,
  });

  static const _devicesKey = 'phone_remote.devices.v1';

  final MetadataStorage _metadataStorage;
  final CredentialStorage _credentialStorage;
  Future<void> _mutationQueue = Future<void>.value();

  @override
  Future<List<Device>> getAll() async {
    await _mutationQueue;
    return _readAll();
  }

  Future<List<Device>> _readAll() async {
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
    await _mutationQueue;
    return _findByServerId(serverId);
  }

  Future<Device?> _findByServerId(String serverId) async {
    for (final device in await _readAll()) {
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
        'A paired device and non-empty credential are required.',
      );
    }
    return _serializeMutation(() async {
      final existing = await _findByServerId(device.serverId);
      final oldReference = existing?.credentialReference;
      final previousCredential = await _credentialStorage.read(reference);
      await _credentialStorage.write(reference, credential);
      String? oldCredential;
      try {
        if (oldReference != null && oldReference != reference) {
          oldCredential = await _credentialStorage.read(oldReference);
          await _credentialStorage.delete(oldReference);
        }
        await _save(device);
      } catch (error, stackTrace) {
        try {
          if (previousCredential == null) {
            await _credentialStorage.delete(reference);
          } else {
            await _credentialStorage.write(reference, previousCredential);
          }
          if (oldReference != null &&
              oldReference != reference &&
              oldCredential != null) {
            await _credentialStorage.write(oldReference, oldCredential);
          }
        } on Object {
          // Preserve the metadata failure, which is the reason the operation
          // could not be committed.
        }
        Error.throwWithStackTrace(error, stackTrace);
      }
    });
  }

  @override
  Future<void> save(Device device) => _serializeMutation(() => _save(device));

  Future<void> _save(Device device) async {
    final devices = (await _readAll()).toList();
    final existingIndex = devices.indexWhere(
      (candidate) =>
          candidate.id == device.id || candidate.serverId == device.serverId,
    );
    if (existingIndex == -1) {
      devices.add(device);
    } else {
      final existing = devices[existingIndex];
      devices[existingIndex] = device.copyWith(id: existing.id);
    }
    devices.sort(_compareDevices);
    await _metadataStorage.write(
      _devicesKey,
      jsonEncode(devices.map((item) => item.toJson()).toList()),
    );
  }

  @override
  Future<String?> readCredential(Device device) async {
    await _mutationQueue;
    final reference = device.credentialReference;
    return reference == null ? null : _credentialStorage.read(reference);
  }

  @override
  Future<void> remove(Device device) => _serializeMutation(() async {
    final devices = (await _readAll())
        .where((candidate) => candidate.id != device.id)
        .toList();
    final reference = device.credentialReference;
    final credential = reference == null
        ? null
        : await _credentialStorage.read(reference);
    if (reference != null) {
      await _credentialStorage.delete(reference);
    }
    try {
      await _metadataStorage.write(
        _devicesKey,
        jsonEncode(devices.map((item) => item.toJson()).toList()),
      );
    } catch (error, stackTrace) {
      if (reference != null && credential != null) {
        try {
          await _credentialStorage.write(reference, credential);
        } on Object {
          // Preserve the metadata failure reported to the caller.
        }
      }
      Error.throwWithStackTrace(error, stackTrace);
    }
  });

  Future<T> _serializeMutation<T>(Future<T> Function() mutation) {
    final result = _mutationQueue.then((_) => mutation());
    _mutationQueue = result.then<void>(
      (_) {},
      onError: (Object _, StackTrace _) {},
    );
    return result;
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
          serverIdentity: 'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd',
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
    final index = _devices.indexWhere(
      (item) => item.serverId == device.serverId,
    );
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
