import 'package:phone_remote/models/api_models.dart';
import 'package:phone_remote/models/server_endpoint.dart';
import 'package:phone_remote/services/api_client.dart';

class FakeApiClientFactory implements ApiClientFactory {
  FakeApiClientFactory({
    required this.info,
    required this.session,
    required this.result,
    this.status,
    this.apps = const <ConfiguredApp>[],
  });

  final ServerInfo info;
  final PairingSession session;
  PairingResult result;
  final ServerStatus? status;
  final List<ConfiguredApp> apps;
  final List<ApiClientInvocation> invocations = <ApiClientInvocation>[];
  final List<FakeApiClient> clients = <FakeApiClient>[];
  final List<String> commands = <String>[];

  @override
  PhoneRemoteApiClient create(
    ServerEndpoint endpoint, {
    String? trustedIdentity,
    String? expectedServerId,
    String? credential,
  }) {
    invocations.add(
      ApiClientInvocation(
        endpoint: endpoint,
        trustedIdentity: trustedIdentity,
        expectedServerId: expectedServerId,
        credential: credential,
      ),
    );
    final client = FakeApiClient(this);
    clients.add(client);
    return client;
  }
}

class ApiClientInvocation {
  const ApiClientInvocation({
    required this.endpoint,
    required this.trustedIdentity,
    required this.expectedServerId,
    required this.credential,
  });

  final ServerEndpoint endpoint;
  final String? trustedIdentity;
  final String? expectedServerId;
  final String? credential;
}

class FakeApiClient implements PhoneRemoteApiClient {
  FakeApiClient(this.factory);

  final FakeApiClientFactory factory;
  bool closed = false;

  @override
  Future<ServerInfo> getInfo() async => factory.info;

  @override
  Future<PairingSession> requestPairing() async => factory.session;

  @override
  Future<PairingResult> completePairing({
    required String sessionId,
    required String code,
    required String deviceName,
    required String platform,
  }) async =>
      factory.result;

  @override
  Future<ServerStatus> getStatus() async =>
      factory.status ??
      ServerStatus(
        serverId: factory.info.serverId,
        name: factory.info.name,
        version: factory.info.version,
        apiVersion: factory.info.apiVersion,
        addresses: const <String>['192.168.1.20'],
        port: 8765,
        configOk: true,
      );

  @override
  Future<List<ConfiguredApp>> getApps() async => factory.apps;

  @override
  Future<void> launchApp(String appId) async =>
      factory.commands.add('launch:$appId');

  @override
  Future<void> sendAction(String action) async =>
      factory.commands.add('action:$action');

  @override
  Future<void> sendMouseMove(double dx, double dy) async =>
      factory.commands.add('move:$dx:$dy');

  @override
  Future<void> sendMouseClick({String button = 'left'}) async =>
      factory.commands.add('click:$button');

  @override
  Future<void> sendMouseDoubleClick() async => factory.commands.add('double');

  @override
  Future<void> sendMouseWheel(double delta) async =>
      factory.commands.add('wheel:$delta');

  @override
  Future<void> sendText(String text) async =>
      factory.commands.add('text:$text');

  @override
  Future<void> sendPowerAction(String action) async =>
      factory.commands.add('power:$action');

  @override
  void close() => closed = true;
}
