"""Background worker for non-blocking PyQt6 operations.

Provides thread pool management for long-running tasks without blocking the UI.
Uses QThreadPool and QRunnable for safe thread-based operations.
"""

from typing import Any, Callable, Optional
from PyQt6.QtCore import QRunnable, QThreadPool, pyqtSignal, QObject

from quantum_terminal.utils.logger import get_logger

logger = get_logger(__name__)


class WorkerSignals(QObject):
    """Signals emitted by background workers.

    Signals:
        started: Emitted when task starts.
        finished: Emitted when task completes (with result).
        error: Emitted on exception (with exception info).
        progress: Emitted periodically for progress updates (with value).
    """

    started = pyqtSignal()
    finished = pyqtSignal(object)  # Result
    error = pyqtSignal(Exception, str)  # Exception, traceback
    progress = pyqtSignal(int)  # Progress value


class BackgroundWorker(QRunnable):
    """Background worker for non-blocking tasks.

    Wraps a function to run in a thread pool without blocking the UI.
    Emits signals for task lifecycle events.

    Examples:
        >>> def long_task(ticker):
        ...     return fetch_fundamentals(ticker)
        >>> worker = BackgroundWorker(long_task, "AAPL")
        >>> worker.signals.finished.connect(handle_result)
        >>> worker.signals.error.connect(handle_error)
        >>> BackgroundWorkerManager.instance().run(worker)
    """

    def __init__(
        self,
        func: Callable,
        *args,
        **kwargs,
    ):
        """Initialize background worker.

        Args:
            func: Function to execute in background.
            *args: Positional arguments for function.
            **kwargs: Keyword arguments for function.
        """
        super().__init__()

        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.is_running = False

        logger.debug(f"BackgroundWorker created for {func.__name__}")

    def run(self) -> None:
        """Execute the worker task.

        Runs the function with error handling and signal emission.
        This is called by the thread pool and should not be called directly.
        """
        self.is_running = True

        try:
            logger.debug(f"Worker starting: {self.func.__name__}")
            self.signals.started.emit()

            # Execute function
            result = self.func(*self.args, **self.kwargs)

            logger.debug(f"Worker finished: {self.func.__name__}")
            self.signals.finished.emit(result)

        except Exception as e:
            import traceback

            tb_str = traceback.format_exc()
            logger.error(f"Worker error in {self.func.__name__}: {e}\n{tb_str}")
            self.signals.error.emit(e, tb_str)

        finally:
            self.is_running = False

    def stop(self) -> None:
        """Request worker stop (graceful shutdown).

        Note: May not stop immediately for long-running operations.
        """
        self.is_running = False
        logger.debug(f"Worker stop requested: {self.func.__name__}")


class ProgressWorker(BackgroundWorker):
    """Background worker with progress reporting.

    Extends BackgroundWorker to support progress updates during execution.

    Examples:
        >>> def download_with_progress(tickers, callback):
        ...     for i, ticker in enumerate(tickers):
        ...         fetch_quote(ticker)
        ...         callback(int((i+1)/len(tickers)*100))
        >>> worker = ProgressWorker(download_with_progress, tickers)
        >>> worker.signals.progress.connect(update_progress_bar)
        >>> BackgroundWorkerManager.instance().run(worker)
    """

    def __init__(
        self,
        func: Callable,
        *args,
        **kwargs,
    ):
        """Initialize progress worker.

        Args:
            func: Function accepting a progress callback parameter.
            *args: Positional arguments.
            **kwargs: Keyword arguments.
        """
        super().__init__(func, *args, **kwargs)

        # Add progress_callback to kwargs
        self.kwargs["progress_callback"] = self.signals.progress.emit

    def run(self) -> None:
        """Execute worker with progress reporting."""
        self.is_running = True

        try:
            logger.debug(f"ProgressWorker starting: {self.func.__name__}")
            self.signals.started.emit()

            # Execute function (it will call progress_callback)
            result = self.func(*self.args, **self.kwargs)

            logger.debug(f"ProgressWorker finished: {self.func.__name__}")
            self.signals.finished.emit(result)

        except Exception as e:
            import traceback

            tb_str = traceback.format_exc()
            logger.error(f"ProgressWorker error: {e}\n{tb_str}")
            self.signals.error.emit(e, tb_str)

        finally:
            self.is_running = False


class BackgroundWorkerManager:
    """Singleton manager for background worker thread pool.

    Manages the PyQt6 QThreadPool and provides convenient methods
    to queue and manage background tasks.
    """

    _instance: Optional["BackgroundWorkerManager"] = None
    _pool: Optional[QThreadPool] = None

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize worker manager."""
        if self._initialized:
            return

        self._initialized = True

        # Use global thread pool
        self._pool = QThreadPool.globalInstance()

        # Set reasonable thread limits
        max_threads = max(2, self._pool.maxThreadCount() // 2)
        self._pool.setMaxThreadCount(max_threads)

        logger.info(f"BackgroundWorkerManager initialized: max_threads={max_threads}")

    @staticmethod
    def instance() -> "BackgroundWorkerManager":
        """Get singleton instance.

        Returns:
            BackgroundWorkerManager instance.

        Examples:
            >>> manager = BackgroundWorkerManager.instance()
            >>> worker = BackgroundWorker(task_func)
            >>> manager.run(worker)
        """
        return BackgroundWorkerManager()

    def run(self, worker: BackgroundWorker) -> None:
        """Queue worker for execution.

        Args:
            worker: BackgroundWorker instance to run.

        Raises:
            ValueError: If worker is not a BackgroundWorker instance.

        Examples:
            >>> def load_data():
            ...     return fetch_market_data()
            >>> worker = BackgroundWorker(load_data)
            >>> BackgroundWorkerManager.instance().run(worker)
        """
        if not isinstance(worker, BackgroundWorker):
            raise ValueError(f"Expected BackgroundWorker, got {type(worker)}")

        try:
            self._pool.start(worker)
            logger.debug(f"Worker queued: {worker.func.__name__} (active: {self._pool.activeThreadCount()})")
        except Exception as e:
            logger.error(f"Failed to queue worker: {e}")
            worker.signals.error.emit(e, str(e))

    def run_task(
        self,
        func: Callable,
        *args,
        on_success: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[Exception, str], None]] = None,
        **kwargs,
    ) -> BackgroundWorker:
        """Convenience method to run a function in background.

        Args:
            func: Function to execute.
            *args: Function arguments.
            on_success: Callback on successful completion (receives result).
            on_error: Callback on error (receives exception, traceback).
            **kwargs: Function keyword arguments.

        Returns:
            BackgroundWorker instance for further control.

        Examples:
            >>> def on_success(result):
            ...     print(f"Got data: {result}")
            >>> manager = BackgroundWorkerManager.instance()
            >>> manager.run_task(
            ...     fetch_quote,
            ...     "AAPL",
            ...     on_success=on_success
            ... )
        """
        worker = BackgroundWorker(func, *args, **kwargs)

        if on_success:
            worker.signals.finished.connect(on_success)

        if on_error:
            worker.signals.error.connect(on_error)

        self.run(worker)
        return worker

    def wait_for_all(self, timeout_ms: Optional[int] = None) -> bool:
        """Wait for all background workers to complete.

        Args:
            timeout_ms: Maximum time to wait in milliseconds. None = wait forever.

        Returns:
            True if all workers finished, False if timeout.

        Examples:
            >>> manager = BackgroundWorkerManager.instance()
            >>> manager.wait_for_all(5000)  # Wait up to 5 seconds
        """
        if timeout_ms is not None:
            return self._pool.waitForDone(timeout_ms)
        else:
            # PyQt6 might not have infinite timeout, use large number
            return self._pool.waitForDone(2**31 - 1)

    def get_active_count(self) -> int:
        """Get number of active workers.

        Returns:
            Number of currently running workers.
        """
        return self._pool.activeThreadCount()

    def get_max_threads(self) -> int:
        """Get maximum thread count.

        Returns:
            Maximum number of concurrent threads.
        """
        return self._pool.maxThreadCount()

    def set_max_threads(self, count: int) -> None:
        """Set maximum thread count.

        Args:
            count: Maximum number of concurrent threads.

        Raises:
            ValueError: If count < 1.
        """
        if count < 1:
            raise ValueError("Max threads must be >= 1")

        self._pool.setMaxThreadCount(count)
        logger.info(f"Max threads updated: {count}")

    def clear_all(self) -> None:
        """Clear all queued workers (graceful).

        Note: Does not stop currently running workers.
        """
        try:
            # PyQt6 doesn't have a direct clear method, but we can wait
            self._pool.clear()
            logger.info("Worker queue cleared")
        except AttributeError:
            logger.warning("QThreadPool.clear() not available in this PyQt6 version")
