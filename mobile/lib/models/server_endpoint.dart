class ServerEndpoint {
  const ServerEndpoint({required this.host, this.port = 8765});

  final String host;
  final int port;

  Uri apiUri(String path) {
    final normalizedPath = path.startsWith('/') ? path : '/$path';
    return Uri(
      scheme: 'https',
      host: host,
      port: port,
      path: '/api/v1$normalizedPath',
    );
  }

  Uri resourceUri(Uri path) {
    if (path.hasScheme ||
        path.hasAuthority ||
        path.hasFragment ||
        !path.path.startsWith('/app-icons/') ||
        path.pathSegments.contains('..')) {
      throw const FormatException(
        'Resource path must be relative to the paired PC.',
      );
    }
    return Uri(
      scheme: 'https',
      host: host,
      port: port,
      path: path.path,
      query: path.hasQuery ? path.query : null,
    );
  }

  factory ServerEndpoint.parse(String input) {
    final trimmed = input.trim();
    if (trimmed.isEmpty) {
      throw const FormatException('Enter a computer address.');
    }
    final source = trimmed.contains('://') ? trimmed : 'https://$trimmed';
    final uri = Uri.tryParse(source);
    if (uri == null ||
        uri.scheme != 'https' ||
        uri.host.isEmpty ||
        uri.userInfo.isNotEmpty ||
        uri.hasQuery ||
        uri.hasFragment ||
        (uri.path.isNotEmpty && uri.path != '/')) {
      throw const FormatException(
        'Use a host or IP address, optionally followed by a port.',
      );
    }
    final port = uri.hasPort ? uri.port : 8765;
    if (port < 1 || port > 65535) {
      throw const FormatException('The port must be between 1 and 65535.');
    }
    return ServerEndpoint(host: uri.host, port: port);
  }

  @override
  String toString() => port == 8765 ? host : '$host:$port';

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is ServerEndpoint && host == other.host && port == other.port;

  @override
  int get hashCode => Object.hash(host, port);
}
