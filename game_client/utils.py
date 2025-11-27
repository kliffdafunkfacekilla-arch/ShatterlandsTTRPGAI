import threading
import logging
from kivy.clock import mainthread

class AsyncHelper:
    """Mixin to offload tasks to a background thread."""
    
    def run_async(self, task_func, success_callback, error_callback=None):
        """
        Run task_func in a thread.
        
        :param task_func: Function to run in background (no args).
        :param success_callback: Function to run on main thread with result.
        :param error_callback: Function to run on main thread if exception occurs.
        """
        def worker():
            try:
                result = task_func()
                self._dispatch_success(success_callback, result)
            except Exception as e:
                self._dispatch_error(error_callback, e)

        threading.Thread(target=worker, daemon=True).start()

    @mainthread
    def _dispatch_success(self, callback, result):
        callback(result)

    @mainthread
    def _dispatch_error(self, callback, error):
        if callback:
            callback(error)
        else:
            # Default error handling: Log to console
            logging.error(f"Async Task Failed: {error}")
