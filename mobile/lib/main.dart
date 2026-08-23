import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'application/phone_remote_controller.dart';
import 'data/storage.dart';
import 'localization.dart';
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
  late Locale _locale;

  @override
  void initState() {
    super.initState();
    final systemLanguage =
        WidgetsBinding.instance.platformDispatcher.locale.languageCode;
    _locale = Locale(systemLanguage == 'zh' ? 'zh' : 'en');
    _initialization = widget.controller.initialize();
    _loadLanguage();
  }

  Future<void> _loadLanguage() async {
    try {
      final saved =
          await SharedPreferencesAsync().getString('phone-remote-language');
      if (mounted && (saved == 'zh' || saved == 'en')) {
        setState(() => _locale = Locale(saved!));
      }
    } on Object {
      // The system-language default remains available without preference storage.
    }
  }

  void _setLocale(Locale locale) {
    if (locale.languageCode != 'zh' && locale.languageCode != 'en') return;
    setState(() => _locale = Locale(locale.languageCode));
    SharedPreferencesAsync()
        .setString('phone-remote-language', locale.languageCode)
        .catchError((_) {});
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Phone Remote',
      debugShowCheckedModeBanner: false,
      locale: _locale,
      supportedLocales: const <Locale>[Locale('zh'), Locale('en')],
      localizationsDelegates: const <LocalizationsDelegate<dynamic>>[
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF126E82),
          brightness: Brightness.light,
        ),
        useMaterial3: true,
      ),
      builder: (context, child) => AppLanguageScope(
        locale: _locale,
        onLocaleChanged: _setLocale,
        child: child!,
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
                    '${context.tr('Unable to load saved devices.')}\n${snapshot.error}',
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
