class ServerInfo {
  const ServerInfo({
    required this.serverId,
    required this.name,
    required this.version,
    required this.apiVersion,
    required this.pairing,
    required this.identityFingerprint,
    required this.certificateFingerprint,
  });

  final String serverId;
  final String name;
  final String version;
  final int apiVersion;
  final bool pairing;
  final String identityFingerprint;
  final String certificateFingerprint;

  factory ServerInfo.fromJson(Map<String, Object?> json) {
    return ServerInfo(
      serverId: _string(json, 'serverId'),
      name: _string(json, 'name'),
      version: _string(json, 'version'),
      apiVersion: _integer(json, 'apiVersion'),
      pairing: _boolean(json, 'pairing'),
      identityFingerprint: _fingerprint(json, 'identityFingerprint'),
      certificateFingerprint: _fingerprint(json, 'certificateFingerprint'),
    );
  }
}

class PairingSession {
  const PairingSession({required this.sessionId, required this.expiresIn});

  final String sessionId;
  final int expiresIn;

  factory PairingSession.fromJson(Map<String, Object?> json) {
    final expiresIn = _integer(json, 'expiresIn');
    if (expiresIn < 1 || expiresIn > 300) {
      throw const FormatException('Invalid pairing expiration.');
    }
    return PairingSession(
      sessionId: _string(json, 'sessionId'),
      expiresIn: expiresIn,
    );
  }
}

class PairingResult {
  const PairingResult({
    required this.clientId,
    required this.credential,
    required this.serverId,
    required this.identityFingerprint,
  });

  final String clientId;
  final String credential;
  final String serverId;
  final String identityFingerprint;

  factory PairingResult.fromJson(Map<String, Object?> json) {
    return PairingResult(
      clientId: _string(json, 'clientId'),
      credential: _string(json, 'credential'),
      serverId: _string(json, 'serverId'),
      identityFingerprint: _fingerprint(json, 'identityFingerprint'),
    );
  }
}

class ServerStatus {
  const ServerStatus({
    required this.serverId,
    required this.name,
    required this.version,
    required this.apiVersion,
    required this.addresses,
    required this.port,
    required this.configOk,
    this.configError,
    this.wakeTargets = const <WakeTarget>[],
  });

  final String serverId;
  final String name;
  final String version;
  final int apiVersion;
  final List<String> addresses;
  final int port;
  final bool configOk;
  final String? configError;
  final List<WakeTarget> wakeTargets;

  factory ServerStatus.fromJson(Map<String, Object?> json) {
    final rawAddresses = json['addresses'];
    if (rawAddresses is! List<Object?> ||
        rawAddresses.any((address) => address is! String || address.isEmpty)) {
      throw const FormatException('addresses must be a list of IP addresses.');
    }
    final port = _integer(json, 'port');
    if (port < 1 || port > 65535) {
      throw const FormatException('port must be a valid TCP port.');
    }
    final rawWakeTargets = json['wakeTargets'];
    final wakeTargets = <WakeTarget>[];
    if (rawWakeTargets != null) {
      if (rawWakeTargets is! List<Object?>) {
        throw const FormatException('wakeTargets must be a list.');
      }
      for (final value in rawWakeTargets) {
        if (value is! Map<String, Object?>) {
          throw const FormatException('Wake target must be an object.');
        }
        wakeTargets.add(WakeTarget.fromJson(value));
      }
    }
    return ServerStatus(
      serverId: _string(json, 'serverId'),
      name: _string(json, 'name'),
      version: _string(json, 'version'),
      apiVersion: _integer(json, 'apiVersion'),
      addresses: List<String>.unmodifiable(rawAddresses.cast<String>()),
      port: port,
      configOk: _boolean(json, 'configOk'),
      configError: _nullableString(json, 'configError'),
      wakeTargets: List<WakeTarget>.unmodifiable(wakeTargets),
    );
  }
}

class WakeTarget {
  const WakeTarget({
    required this.mac,
    required this.address,
    required this.broadcast,
  });

  final String mac;
  final String address;
  final String broadcast;

  factory WakeTarget.fromJson(Map<String, Object?> json) {
    final mac = _string(json, 'mac');
    final normalizedMac = mac.replaceAll(RegExp(r'[^a-fA-F0-9]'), '');
    if (!RegExp(r'^[a-fA-F0-9]{12}$').hasMatch(normalizedMac)) {
      throw const FormatException('Wake target MAC address is invalid.');
    }
    return WakeTarget(
      mac: mac,
      address: _string(json, 'address'),
      broadcast: _string(json, 'broadcast'),
    );
  }
}

class ConfiguredApp {
  const ConfiguredApp({
    required this.id,
    required this.name,
    required this.available,
    required this.icon,
  });

  final String id;
  final String name;
  final bool available;
  final String icon;

  factory ConfiguredApp.fromJson(Map<String, Object?> json) {
    final id = _string(json, 'id');
    if (!RegExp(r'^[a-z0-9][a-z0-9_-]{0,31}$').hasMatch(id)) {
      throw const FormatException('Configured app ID is invalid.');
    }
    return ConfiguredApp(
      id: id,
      name: _string(json, 'name'),
      available: _boolean(json, 'available'),
      icon: _string(json, 'icon'),
    );
  }
}

String _string(Map<String, Object?> json, String key) {
  final value = json[key];
  if (value is! String || value.isEmpty) {
    throw FormatException('$key must be a non-empty string.');
  }
  return value;
}

int _integer(Map<String, Object?> json, String key) {
  final value = json[key];
  if (value is! int) {
    throw FormatException('$key must be an integer.');
  }
  return value;
}

bool _boolean(Map<String, Object?> json, String key) {
  final value = json[key];
  if (value is! bool) {
    throw FormatException('$key must be a boolean.');
  }
  return value;
}

String? _nullableString(Map<String, Object?> json, String key) {
  final value = json[key];
  if (value == null) {
    return null;
  }
  if (value is! String || value.isEmpty) {
    throw FormatException('$key must be null or a non-empty string.');
  }
  return value;
}

String _fingerprint(Map<String, Object?> json, String key) {
  final value = _string(json, key).toLowerCase();
  if (!RegExp(r'^[a-f0-9]{64}$').hasMatch(value)) {
    throw FormatException('$key must be a SHA-256 fingerprint.');
  }
  return value;
}
