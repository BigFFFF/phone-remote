import 'package:flutter/material.dart';

import '../application/phone_remote_controller.dart';
import '../localization.dart';
import 'find_computers_screen.dart';

class WelcomeScreen extends StatelessWidget {
  const WelcomeScreen({super.key, required this.controller});

  final PhoneRemoteController controller;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              Align(
                alignment: Alignment.centerRight,
                child: DropdownButton<String>(
                  value: Localizations.localeOf(context).languageCode,
                  items: const <DropdownMenuItem<String>>[
                    DropdownMenuItem<String>(value: 'zh', child: Text('中文')),
                    DropdownMenuItem<String>(
                        value: 'en', child: Text('English')),
                  ],
                  onChanged: (value) {
                    if (value != null) {
                      AppLanguageScope.maybeOf(context)
                          ?.onLocaleChanged(Locale(value));
                    }
                  },
                ),
              ),
              const Spacer(),
              Icon(
                Icons.phone_android_rounded,
                size: 72,
                color: Theme.of(context).colorScheme.primary,
              ),
              const SizedBox(height: 32),
              Text(
                'Phone Remote',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.displaySmall?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
              ),
              const SizedBox(height: 16),
              Text(
                context.tr('Control your Windows PC\nfrom your phone.'),
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
              ),
              const Spacer(),
              FilledButton(
                onPressed: () {
                  Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) =>
                          FindComputersScreen(controller: controller),
                    ),
                  );
                },
                child: Text(context.tr('Get Started')),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
