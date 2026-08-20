import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../application/phone_remote_controller.dart';
import '../services/api_client.dart';
import '../services/pairing_service.dart';

class PairingScreen extends StatefulWidget {
  const PairingScreen({
    super.key,
    required this.controller,
    required this.attempt,
  });

  final PhoneRemoteController controller;
  final PairingAttempt attempt;

  @override
  State<PairingScreen> createState() => _PairingScreenState();
}

class _PairingScreenState extends State<PairingScreen> {
  final _codeController = TextEditingController();
  bool _submitting = false;
  String? _error;

  @override
  void dispose() {
    _codeController.dispose();
    super.dispose();
  }

  Future<void> _complete() async {
    if (_submitting) {
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      await widget.controller.completePairing(
        attempt: widget.attempt,
        code: _codeController.text,
        deviceName: Platform.localHostname,
        platform: Platform.operatingSystem,
      );
      if (mounted) {
        Navigator.of(context).popUntil((route) => route.isFirst);
      }
    } on FormatException catch (error) {
      setState(() => _error = error.message.toString());
    } on ApiException catch (error) {
      setState(() => _error = error.message);
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Pair securely')),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: <Widget>[
          const Icon(Icons.phonelink_lock_rounded, size: 72),
          const SizedBox(height: 24),
          Text(
            widget.attempt.server.name,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 12),
          const Text(
            'Enter the six-digit code shown by Phone Remote on your Windows PC.',
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 32),
          TextField(
            controller: _codeController,
            autofocus: true,
            keyboardType: TextInputType.number,
            textAlign: TextAlign.center,
            textInputAction: TextInputAction.done,
            maxLength: 6,
            inputFormatters: <TextInputFormatter>[
              FilteringTextInputFormatter.digitsOnly,
            ],
            style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                  letterSpacing: 12,
                ),
            decoration: InputDecoration(
              labelText: 'Pairing code',
              errorText: _error,
            ),
            onSubmitted: (_) => _complete(),
          ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: _submitting ? null : _complete,
            child: _submitting
                ? const SizedBox.square(
                    dimension: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Pair'),
          ),
          const SizedBox(height: 16),
          Text(
            'The code expires in ${widget.attempt.session.expiresIn ~/ 60} minutes.',
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }
}
