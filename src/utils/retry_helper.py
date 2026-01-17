"""
Retry Helper Module
===================
API cagrilari ve network islemleri icin retry logic.
Exponential backoff ile tekrar deneme mekanizmasi.
"""

import time
import logging
import functools
from typing import TypeVar, Callable, Optional, Type, Tuple, Any

# Config import
try:
    from ..config.constants import CONFIG
except ImportError:
    CONFIG = None

logger = logging.getLogger(__name__)

# Generic return type
T = TypeVar('T')


def get_retry_config():
    """Retry konfigurasyonunu al."""
    if CONFIG:
        return CONFIG.retry
    # Fallback defaults
    class DefaultRetry:
        MAX_ATTEMPTS = 3
        MIN_WAIT = 2
        MAX_WAIT = 10
        MULTIPLIER = 1.5
    return DefaultRetry()


def retry_with_backoff(
    max_attempts: Optional[int] = None,
    min_wait: Optional[float] = None,
    max_wait: Optional[float] = None,
    multiplier: Optional[float] = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
) -> Callable:
    """
    Exponential backoff ile retry decorator.

    Args:
        max_attempts: Maksimum deneme sayisi
        min_wait: Minimum bekleme suresi (saniye)
        max_wait: Maksimum bekleme suresi (saniye)
        multiplier: Backoff carpani
        exceptions: Yakalanacak exception turleri
        on_retry: Her retry'da cagrilacak callback

    Usage:
        @retry_with_backoff(max_attempts=3, exceptions=(APIError,))
        def call_api():
            ...
    """
    config = get_retry_config()

    _max_attempts = max_attempts or config.MAX_ATTEMPTS
    _min_wait = min_wait or config.MIN_WAIT
    _max_wait = max_wait or config.MAX_WAIT
    _multiplier = multiplier or config.MULTIPLIER

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            wait_time = _min_wait

            for attempt in range(1, _max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == _max_attempts:
                        logger.error(
                            f"[{func.__name__}] Tum denemeler basarisiz "
                            f"({_max_attempts} deneme): {e}"
                        )
                        raise

                    # On retry callback
                    if on_retry:
                        on_retry(e, attempt)

                    logger.warning(
                        f"[{func.__name__}] Deneme {attempt}/{_max_attempts} "
                        f"basarisiz: {e}. {wait_time:.1f}s sonra tekrar deneniyor..."
                    )

                    time.sleep(wait_time)

                    # Exponential backoff
                    wait_time = min(wait_time * _multiplier, _max_wait)

            # Should not reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


def retry_api_call(
    func: Callable[..., T],
    *args,
    max_attempts: int = 3,
    api_exceptions: Tuple[Type[Exception], ...] = None,
    **kwargs
) -> T:
    """
    API cagrisini retry ile calistir (fonksiyonel versiyon).

    Args:
        func: Cagrilacak fonksiyon
        *args: Fonksiyon argumanlari
        max_attempts: Maksimum deneme sayisi
        api_exceptions: Yakalanacak exception turleri
        **kwargs: Fonksiyon keyword argumanlari

    Returns:
        Fonksiyon sonucu

    Usage:
        result = retry_api_call(client.send_message, prompt, max_attempts=3)
    """
    # Varsayilan API exception'lari
    if api_exceptions is None:
        try:
            import anthropic
            api_exceptions = (
                anthropic.APIConnectionError,
                anthropic.RateLimitError,
                anthropic.APITimeoutError,
                ConnectionError,
                TimeoutError
            )
        except ImportError:
            api_exceptions = (ConnectionError, TimeoutError, Exception)

    config = get_retry_config()
    wait_time = config.MIN_WAIT
    last_exception = None

    for attempt in range(1, max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except api_exceptions as e:
            last_exception = e

            if attempt == max_attempts:
                logger.error(f"API call failed after {max_attempts} attempts: {e}")
                raise

            logger.warning(
                f"API call attempt {attempt}/{max_attempts} failed: {e}. "
                f"Retrying in {wait_time:.1f}s..."
            )

            time.sleep(wait_time)
            wait_time = min(wait_time * config.MULTIPLIER, config.MAX_WAIT)

    if last_exception:
        raise last_exception


class RetryableAPIClient:
    """
    Retry logic ile sarmalanmis API client wrapper.

    Usage:
        client = RetryableAPIClient(anthropic.Anthropic())
        response = client.call(
            client.messages.create,
            model="claude-opus-4-5-20250514",
            messages=[...]
        )
    """

    def __init__(
        self,
        client: Any,
        max_attempts: int = None,
        min_wait: float = None,
        max_wait: float = None
    ):
        self.client = client
        config = get_retry_config()
        self.max_attempts = max_attempts or config.MAX_ATTEMPTS
        self.min_wait = min_wait or config.MIN_WAIT
        self.max_wait = max_wait or config.MAX_WAIT
        self.multiplier = config.MULTIPLIER

    def call(self, method: Callable[..., T], *args, **kwargs) -> T:
        """Retry ile method cagir."""
        return retry_api_call(
            method,
            *args,
            max_attempts=self.max_attempts,
            **kwargs
        )

    def __getattr__(self, name: str) -> Any:
        """Client attribute'larina erisim."""
        return getattr(self.client, name)
