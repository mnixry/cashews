import logging
from functools import wraps
from typing import Any, Callable, NoReturn, Optional

from ..backends.interface import Backend
from ..exceptions import RateLimitError
from ..formatter import register_template
from ..key import get_cache_key, get_cache_key_template
from .._typing import Callable_T

logger = logging.getLogger(__name__)




def _default_action(*args: Any, **kwargs: Any) -> NoReturn:
    raise RateLimitError()


def rate_limit(
    backend: Backend,
    limit: int,
    period: int,
    ttl: Optional[int] = None,
    key: Optional[str] = None,
    action: Optional[Callable] = None,
    prefix: str = "rate_limit",
):  # pylint: disable=too-many-arguments
    """
    Rate limit for function call. Do not call function if rate limit is reached, and call given action

    :param backend: cache backend
    :param limit: number of calls
    :param period: Period
    :param ttl: time ban, default == period
    :param action: call when rate limit reached, default raise RateLimitError
    :param prefix: custom prefix for key, default 'rate_limit'
    """
    action = _default_action if action is None else action

    def decorator(func: Callable_T) -> Callable_T:
        _key_template = get_cache_key_template(func, key=key, prefix=prefix)
        register_template(func, _key_template)

        @wraps(func)
        async def wrapped_func(*args, **kwargs):
            _cache_key = get_cache_key(func, _key_template, args, kwargs)

            requests_count = await backend.incr(key=_cache_key)  # set 1 if not exists
            if requests_count and requests_count > limit:
                if ttl and requests_count == limit + 1:
                    await backend.expire(key=_cache_key, timeout=ttl)
                logger.info("Rate limit reach for %s", _cache_key)
                action(*args, **kwargs)

            if requests_count == 1:
                await backend.expire(key=_cache_key, timeout=period)

            return await func(*args, **kwargs)

        return wrapped_func

    return decorator
