import 'dart:async';

typedef PointerMoveSender = Future<void> Function(double dx, double dy);
typedef PointerMoveErrorHandler = void Function(Object error);

class PointerMoveDispatcher {
  PointerMoveDispatcher({
    required this._send,
    this.interval = const Duration(milliseconds: 16),
    this.maxConcurrentSends = 1,
    this.maxAbsoluteDelta = 120,
    this._onError,
  }) : assert(maxConcurrentSends > 0),
        assert(maxAbsoluteDelta > 0);

  final PointerMoveSender _send;
  final PointerMoveErrorHandler? _onError;
  final Duration interval;
  final int maxConcurrentSends;
  final double maxAbsoluteDelta;

  Timer? _timer;
  double _pendingDx = 0;
  double _pendingDy = 0;
  int _inFlight = 0;
  bool _disposed = false;

  void add(double dx, double dy) {
    if (_disposed || (!dx.isFinite || !dy.isFinite)) {
      return;
    }
    _pendingDx += dx;
    _pendingDy += dy;
    _schedule();
  }

  void _schedule() {
    if (_disposed || _timer != null || _inFlight >= maxConcurrentSends) {
      return;
    }
    _timer = Timer(interval, () {
      _timer = null;
      _flush();
    });
  }

  void _flush() {
    if (_disposed || _inFlight >= maxConcurrentSends) {
      return;
    }
    final dx = _takeBounded(_pendingDx);
    final dy = _takeBounded(_pendingDy);
    _pendingDx -= dx;
    _pendingDy -= dy;
    if (dx == 0 && dy == 0) {
      return;
    }
    _inFlight += 1;
    unawaited(_sendBatch(dx, dy));
  }

  double _takeBounded(double value) =>
      value.clamp(-maxAbsoluteDelta, maxAbsoluteDelta).toDouble();

  Future<void> _sendBatch(double dx, double dy) async {
    try {
      await _send(dx, dy);
    } catch (error) {
      if (!_disposed) {
        _onError?.call(error);
      }
    } finally {
      _inFlight -= 1;
      if (_pendingDx != 0 || _pendingDy != 0) {
        _schedule();
      }
    }
  }

  void dispose() {
    _disposed = true;
    _timer?.cancel();
    _timer = null;
    _pendingDx = 0;
    _pendingDy = 0;
  }
}
