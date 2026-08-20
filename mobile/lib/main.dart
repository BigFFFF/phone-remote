import 'dart:io';

import 'package:flutter/material.dart';

import 'application/phone_remote_controller.dart';
import 'data/storage.dart';
import 'repositories/device_repository.dart';
import 'services/api_client.dart';
import 'services/discovery_service.dart';
import 'services/pairing_service.dart';
import 'services/remote_session.dart';
import 'services/wake_service.dart';
import 'ui/remote_shell.dart';
import 'ui/welcome_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  final repository = RealDeviceRepository(
    metadataStorage: SharedPreferencesMetadataStorage(),
    credentialStorage: SecureCredentialStorage(),
  );
  final controller = PhoneRemoteController(
    deviceRepository: repository,
    discoveryService: MdnsDiscoveryService(),
    pairingService: PairingService(
      apiClientFactory: const HttpApiClientFactory(),
      deviceRepository: repository,
    ),
    remoteSessionFactory: RealRemoteSessionFactory(
      deviceRepository: repository,
      apiClientFactory: const HttpApiClientFactory(),
    ),
    wakeService: Platform.isAndroid
        ? UdpWakeService()
        : const UnavailableWakeService(
            'Wake on LAN is unavailable in this iOS build because the required networking entitlement is not enabled.',
          ),
  );
  runApp(PhoneRemoteApp(controller: controller));
}

class PhoneRemoteApp extends StatefulWidget {
  const PhoneRemoteApp({super.key, required this.controller});

  final PhoneRemoteController controller;

  @override
  State<PhoneRemoteApp> createState() => _PhoneRemoteAppState();
}

class _PhoneRemoteAppState extends State<PhoneRemoteApp> {
  late final Future<void> _initialization;

  @override
  void initState() {
    super.initState();
    _initialization = widget.controller.initialize();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Phone Remote',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF126E82),
          brightness: Brightness.light,
        ),
        useMaterial3: true,
      ),
      home: FutureBuilder<void>(
        future: _initialization,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Scaffold(
              body: Center(child: CircularProgressIndicator()),
            );
          }
          if (snapshot.hasError) {
            return Scaffold(
              body: Center(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Text(
                    'Unable to load saved devices.\n${snapshot.error}',
                    textAlign: TextAlign.center,
                  ),
                ),
              ),
            );
          }
          return AnimatedBuilder(
            animation: widget.controller,
            builder: (context, _) => widget.controller.devices.isEmpty
                ? WelcomeScreen(controller: widget.controller)
                : RemoteShell(controller: widget.controller),
          );
        },
      ),
    );
  }
}
