import 'dart:async';

import 'package:multicast_dns/multicast_dns.dart';

class DiscoveredDevice {
  const DiscoveredDevice({
    required this.serverId,
    required this.name,
    required this.host,
    required this.port,
    required this.apiVersion,
    required this.tls,
    this.serverVersion,
    this.identityHint,
  });

  final String serverId;
  final String name;
  final String host;
  final int port;
  final int apiVersion;
  final bool tls;
  final String? serverVersion;
  final String? identityHint;

  DiscoveredDevice copyWith({
    String? name,
    String? host,
    int? port,
    int? apiVersion,
    bool? tls,
    String? serverVersion,
    String? identityHint,
  }) {
    return DiscoveredDevice(
      serverId: serverId,
      name: name ?? this.name,
      host: host ?? this.host,
      port: port ?? this.port,
      apiVersion: apiVersion ?? this.apiVersion,
      tls: tls ?? this.tls,
      serverVersion: serverVersion ?? this.serverVersion,
      identityHint: identityHint ?? this.identityHint,
    );
  }
}

abstract interface class DiscoveryService {
  Future<List<DiscoveredDevice>> discover({
    Duration timeout = const Duration(seconds: 5),
  });
}

class MdnsDiscoveryService implements DiscoveryService {
  static const serviceType = '_phone-remote._tcp.local';

  @override
  Future<List<DiscoveredDevice>> discover({
    Duration timeout = const Duration(seconds: 5),
  }) async {
    final client = MDnsClient();
    await client.start();
    try {
      final pointers = await _collectPointers(client, timeout);
      final resolved = await Future.wait<DiscoveredDevice?>(
        pointers.map((pointer) => _resolve(client, pointer, timeout)),
      );
      return DiscoveryMerger.merge(resolved.whereType<DiscoveredDevice>());
    } finally {
      client.stop();
    }
  }

  Future<List<PtrResourceRecord>> _collectPointers(
    MDnsClient client,
    Duration timeout,
  ) async {
    final pointers = <PtrResourceRecord>[];
    final completed = Completer<void>();
    Timer? quietTimer;
    final deadlineTimer = Timer(timeout, () {
      if (!completed.isCompleted) completed.complete();
    });
    late final StreamSubscription<PtrResourceRecord> subscription;
    subscription = client
        .lookup<PtrResourceRecord>(
          ResourceRecordQuery.serverPointer(serviceType),
          timeout: timeout,
        )
        .listen(
          (pointer) {
            pointers.add(pointer);
            quietTimer?.cancel();
            quietTimer = Timer(const Duration(milliseconds: 600), () {
              if (!completed.isCompleted) completed.complete();
            });
          },
          onError: (Object error, StackTrace stackTrace) {
            if (!completed.isCompleted) {
              completed.completeError(error, stackTrace);
            }
          },
          onDone: () {
            if (!completed.isCompleted) completed.complete();
          },
        );
    try {
      await completed.future;
    } finally {
      deadlineTimer.cancel();
      quietTimer?.cancel();
      await subscription.cancel();
    }
    return pointers;
  }

  Future<DiscoveredDevice?> _resolve(
    MDnsClient client,
    PtrResourceRecord pointer,
    Duration timeout,
  ) async {
    final service = await _firstOrNull<SrvResourceRecord>(
      client.lookup<SrvResourceRecord>(
        ResourceRecordQuery.service(pointer.domainName),
        timeout: timeout,
      ),
    );
    if (service == null) {
      return null;
    }
    final addressFuture = _firstOrNull<IPAddressResourceRecord>(
      client.lookup<IPAddressResourceRecord>(
        ResourceRecordQuery.addressIPv4(service.target),
        timeout: timeout,
      ),
    );
    final textFuture = _firstOrNull<TxtResourceRecord>(
      client.lookup<TxtResourceRecord>(
        ResourceRecordQuery.text(pointer.domainName),
        timeout: timeout,
      ),
    );
    final address = await addressFuture;
    final textRecord = await textFuture;
    if (address == null) {
      return null;
    }
    final properties = <String, String>{};
    if (textRecord != null) {
      for (final line in textRecord.text.split('\n')) {
        final separator = line.indexOf('=');
        if (separator > 0) {
          properties[line.substring(0, separator)] =
              line.substring(separator + 1);
        }
      }
    }
    final serverId = properties['serverId'];
    final name = properties['name'];
    final apiVersion = int.tryParse(properties['apiVersion'] ?? '');
    if (serverId == null ||
        serverId.isEmpty ||
        name == null ||
        name.isEmpty ||
        apiVersion == null) {
      return null;
    }
    return DiscoveredDevice(
      serverId: serverId,
      name: name,
      host: address.address.address,
      port: service.port,
      apiVersion: apiVersion,
      tls: properties['tls'] == '1',
      serverVersion: properties['serverVersion'],
      identityHint: properties['identity'],
    );
  }

  Future<T?> _firstOrNull<T>(Stream<T> stream) async {
    try {
      return await stream.first;
    } on StateError {
      return null;
    }
  }
}

class DiscoveryMerger {
  const DiscoveryMerger._();

  static List<DiscoveredDevice> merge(Iterable<DiscoveredDevice> candidates) {
    final byServerId = <String, DiscoveredDevice>{};
    for (final candidate in candidates) {
      final existing = byServerId[candidate.serverId];
      byServerId[candidate.serverId] = existing == null
          ? candidate
          : existing.copyWith(
              name: candidate.name,
              host: candidate.host,
              port: candidate.port,
              apiVersion: candidate.apiVersion,
              tls: candidate.tls,
              serverVersion: candidate.serverVersion,
              identityHint: candidate.identityHint,
            );
    }
    final devices = byServerId.values.toList()
      ..sort((left, right) =>
          left.name.toLowerCase().compareTo(right.name.toLowerCase()));
    return List<DiscoveredDevice>.unmodifiable(devices);
  }
}
