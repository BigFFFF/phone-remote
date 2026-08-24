const Object _copyWithUnset = Object();

class Device {
  const Device({
    required this.id,
    required this.serverId,
    required this.name,
    required this.host,
    required this.serverIdentity,
    this.port = 8765,
    this.mac,
    this.lastIpv4,
    this.broadcastAddress,
    this.certificateFingerprint,
    this.clientId,
    this.credentialReference,
    this.lastSeen,
    this.favorite = false,
  });

  final String id;
  final String serverId;
  final String name;
  final String host;
  final int port;
  final String? mac;
  final String? lastIpv4;
  final String? broadcastAddress;
  final String serverIdentity;
  final String? certificateFingerprint;
  final String? clientId;
  final String? credentialReference;
  final DateTime? lastSeen;
  final bool favorite;

  bool get isPaired =>
      serverIdentity.isNotEmpty &&
      clientId != null &&
      credentialReference != null;

  Device copyWith({
    String? id,
    String? serverId,
    String? name,
    String? host,
    int? port,
    Object? mac = _copyWithUnset,
    Object? lastIpv4 = _copyWithUnset,
    Object? broadcastAddress = _copyWithUnset,
    String? serverIdentity,
    Object? certificateFingerprint = _copyWithUnset,
    Object? clientId = _copyWithUnset,
    Object? credentialReference = _copyWithUnset,
    Object? lastSeen = _copyWithUnset,
    bool? favorite,
  }) {
    return Device(
      id: id ?? this.id,
      serverId: serverId ?? this.serverId,
      name: name ?? this.name,
      host: host ?? this.host,
      port: port ?? this.port,
      mac: identical(mac, _copyWithUnset) ? this.mac : mac as String?,
      lastIpv4: identical(lastIpv4, _copyWithUnset)
          ? this.lastIpv4
          : lastIpv4 as String?,
      broadcastAddress: identical(broadcastAddress, _copyWithUnset)
          ? this.broadcastAddress
          : broadcastAddress as String?,
      serverIdentity: serverIdentity ?? this.serverIdentity,
      certificateFingerprint: identical(certificateFingerprint, _copyWithUnset)
          ? this.certificateFingerprint
          : certificateFingerprint as String?,
      clientId: identical(clientId, _copyWithUnset)
          ? this.clientId
          : clientId as String?,
      credentialReference: identical(credentialReference, _copyWithUnset)
          ? this.credentialReference
          : credentialReference as String?,
      lastSeen: identical(lastSeen, _copyWithUnset)
          ? this.lastSeen
          : lastSeen as DateTime?,
      favorite: favorite ?? this.favorite,
    );
  }

  Map<String, Object?> toJson() => <String, Object?>{
    'id': id,
    'serverId': serverId,
    'name': name,
    'host': host,
    'port': port,
    'mac': mac,
    'lastIpv4': lastIpv4,
    'broadcastAddress': broadcastAddress,
    'serverIdentity': serverIdentity,
    'certificateFingerprint': certificateFingerprint,
    'clientId': clientId,
    'credentialReference': credentialReference,
    'lastSeen': lastSeen?.toUtc().toIso8601String(),
    'favorite': favorite,
  };

  factory Device.fromJson(Map<String, Object?> json) {
    String requiredString(String key) {
      final value = json[key];
      if (value is! String || value.isEmpty) {
        throw FormatException('Device.$key must be a non-empty string.');
      }
      return value;
    }

    String? optionalString(String key) {
      final value = json[key];
      if (value == null) {
        return null;
      }
      if (value is! String || value.isEmpty) {
        throw FormatException('Device.$key must be a non-empty string.');
      }
      return value;
    }

    final rawPort = json['port'];
    if (rawPort is! int || rawPort < 1 || rawPort > 65535) {
      throw const FormatException('Device.port must be a valid TCP port.');
    }
    final rawFavorite = json['favorite'];
    if (rawFavorite is! bool) {
      throw const FormatException('Device.favorite must be a boolean.');
    }
    final rawLastSeen = optionalString('lastSeen');

    return Device(
      id: requiredString('id'),
      serverId: requiredString('serverId'),
      name: requiredString('name'),
      host: requiredString('host'),
      port: rawPort,
      mac: optionalString('mac'),
      lastIpv4: optionalString('lastIpv4'),
      broadcastAddress: optionalString('broadcastAddress'),
      serverIdentity: requiredString('serverIdentity'),
      certificateFingerprint: optionalString('certificateFingerprint'),
      clientId: optionalString('clientId'),
      credentialReference: optionalString('credentialReference'),
      lastSeen: rawLastSeen == null
          ? null
          : DateTime.parse(rawLastSeen).toUtc(),
      favorite: rawFavorite,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is Device &&
          id == other.id &&
          serverId == other.serverId &&
          name == other.name &&
          host == other.host &&
          port == other.port &&
          mac == other.mac &&
          lastIpv4 == other.lastIpv4 &&
          broadcastAddress == other.broadcastAddress &&
          serverIdentity == other.serverIdentity &&
          certificateFingerprint == other.certificateFingerprint &&
          clientId == other.clientId &&
          credentialReference == other.credentialReference &&
          lastSeen == other.lastSeen &&
          favorite == other.favorite;

  @override
  int get hashCode => Object.hash(
    id,
    serverId,
    name,
    host,
    port,
    mac,
    lastIpv4,
    broadcastAddress,
    serverIdentity,
    certificateFingerprint,
    clientId,
    credentialReference,
    lastSeen,
    favorite,
  );
}
