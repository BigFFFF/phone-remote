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
    final devices = <DiscoveredDevice>[];
    await client.start();
    try {
      final pointers = client.lookup<PtrResourceRecord>(
        ResourceRecordQuery.serverPointer(serviceType),
        timeout: timeout,
      );
      await for (final pointer in pointers) {
        final resolved = await _resolve(client, pointer, timeout);
        if (resolved != null) {
          devices.add(resolved);
        }
      }
    } finally {
      client.stop();
    }
    return DiscoveryMerger.merge(devices);
  }

  Future<DiscoveredDevice?> _resolve(
    MDnsClient client,
    PtrResourceRecord pointer,
    Duration timeout,
  ) async {
    final services = await client
        .lookup<SrvResourceRecord>(
          ResourceRecordQuery.service(pointer.domainName),
          timeout: timeout,
        )
        .toList();
    if (services.isEmpty) {
      return null;
    }
    final service = services.first;
    final addresses = await client
        .lookup<IPAddressResourceRecord>(
          ResourceRecordQuery.addressIPv4(service.target),
          timeout: timeout,
        )
        .toList();
    if (addresses.isEmpty) {
      return null;
    }
    final textRecords = await client
        .lookup<TxtResourceRecord>(
          ResourceRecordQuery.text(pointer.domainName),
          timeout: timeout,
        )
        .toList();
    final properties = <String, String>{};
    for (final record in textRecords) {
      for (final line in record.text.split('\n')) {
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
      host: addresses.first.address.address,
      port: service.port,
      apiVersion: apiVersion,
      tls: properties['tls'] == '1',
      serverVersion: properties['serverVersion'],
      identityHint: properties['identity'],
    );
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
