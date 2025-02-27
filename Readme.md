<h1 align="center">🥔 CASHEWS 🥔</h1>

<p align="center">
    <em>Async cache utils with simple API to build fast and reliable applications</em>
</p>

```bash
pip install cashews
pip install cashews[redis]  # Aioredis is now in redis-py 4.2.0rc1+
pip install cashews[diskcache]
pip install cashews[dill] # can cache in redis more types of objects
pip install cashews[speedup] # for bloom filters
```

---

## Why

Cache plays a significant role in modern applications and everybody want to use all power of async programming and cache.
There are a few advanced techniques with cache and async programming that can help you build simple, fast,
scalable and reliable applications. This library intends to make it easy to implement such techniques.

## Features

- Easy to configure and use
- Decorator-based API, just decorate and play
- Different cache strategies out-of-the-box
- Support for multiple storage backends ([In-memory](#in-memory), [Redis](#redis), [DiskCache](diskcache))
- Set ttl with string (2h5m) or with `timedelta`
- Middlewares
- Client-side cache (10x faster than simple cache with redis)
- Bloom filters
- Different cache invalidation techniques (time-based and function-call based)
- Cache any objects securely with pickle (use [hash key](#redis))
- 2x faster then `aiocache`

## Usage Example

```python
from cashews import cache

cache.setup("mem://")  # configure as in-memory cache, but redis is also supported

# use a decorator-based API
@cache(ttl="3h", key="user:{request.user.uid}")
async def long_running_function(request):
    ...

# or for fine-grained control, use it directly in a function
async def cache_using_function(request):
    await cache.set(key=request.user.uid, value=request.user, expire=60)
    ...
```

## Table of Contents

- [Configuration](#configuration)
- [Available Backends](#available-backends)
- [Basic API](#basic-api)
- [Strategies](#strategies)
  - [Cache condition](#cache-condition)
  - [Keys templating](#template-keys)
- [Cache Invalidation](#cache-invalidation)
  - [Cache invalidation on code change](#cache-invalidation-on-code-change)
- [Detect the source of a result](#detect-the-source-of-a-result)
- [Middleware](#middleware)

### Configuration

`cashews` provides a default cache, that you can setup in two different ways:

```python
from cashews import cache

# via url
cache.setup("redis://0.0.0.0/?db=1&socket_connect_timeout=0.5&safe=0&hash_key=my_secret&enable=1")
# or via kwargs
cache.setup("redis://0.0.0.0/", db=1, wait_for_connection_timeout=0.5, safe=False, hash_key=b"my_key", enable=True)
```

Alternatively, you can create cache instance yourself:

```python
from cashews import Cache

cache = Cache()
cache.setup(...)
```

Optionally, you can disable cache with `enable` parameter:

```python
cache.setup("redis://redis/0?enable=1")
cache.setup("mem://?size=500", enable=False)
```

You can setup different Backends based on a prefix:

```python
cache.setup("redis://redis/0")
cache.setup("mem://?size=500", prefix="user")

await cache.get("accounts")  # will use redis backend
await cache.get("user:1")  # will use memory backend

```

### Available Backends

#### In-memory

In-memory cache uses fixed-sized LRU dict to store values. It checks expiration on `get`
and periodically purge expired keys.

```python
cache.setup("mem://")
cache.setup("mem://?check_interval=10&size=10000")
```

#### Redis

_Requires [redis](https://github.com/redis/redis-py) package._\
_Note: If you must support a legacy code that uses `aioredis`, then install [aioredis](https://github.com/aio-libs/aioredis-py) instead._

This will use Redis as a storage.

This backend uses [pickle](https://docs.python.org/3/library/pickle.html) module to serialize
values, but the cashes can store values with sha1-keyed hash.

Use `hash_key` parameter to protect your application from security vulnerabilities.
Pickle can't serialize any type of objects. In case you need to store more complex types

you can use [dill](https://github.com/uqfoundation/dill) - set `pickle_type="dill"`.
Dill is great, but less performance.
If you need complex serializer for [sqlalchemy](https://docs.sqlalchemy.org/en/14/core/serializer.html) objects you can set `pickle_type="sqlalchemy"`

Any connections errors are suppressed, to disable it use `safe=False` - a `CacheBackendInteractionException` will be raised

If you would like to use [client-side cache](https://redis.io/topics/client-side-caching) set `client_side=True`
Client side cache will add `cashews:` prefix for each key, to customize it use `client_side_prefix` option.

```python
cache.setup("redis://0.0.0.0/?db=1&minsize=10&safe=false&hash_key=my_secret", prefix="func")
cache.setup("redis://0.0.0.0/2", password="my_pass", socket_connect_timeout=0.1, retry_on_timeout=True, hash_key="my_secret")
cache.setup("redis://0.0.0.0", client_side=True, client_side_prefix="my_prefix:", pickle_type="dill")
```

For using secure connections to redis (over ssl) uri should have `rediss` as schema

```python
cache.setup("rediss://0.0.0.0/", ssl_ca_certs="path/to/ca.crt", ssl_keyfile="path/to/client.key",ssl_certfile="path/to/client.crt",)
```

#### DiskCache

_Requires [diskcache](https://github.com/grantjenks/python-diskcache) package._

This will use local sqlite databases (with shards) as storage.

It is a good choice if you don't want to use redis, but you need a shared storage, or your cache takes a lot of local memory.
Also, it is good choice for client side local storage.

You cat setup disk cache with [FanoutCache parameters](http://www.grantjenks.com/docs/diskcache/api.html#fanoutcache)

** Warning ** `cache.keys_match` and `cache.get_match` does not work with this storage (works only if shards are disabled)

```python
cache.setup("disk://")
cache.setup("disk://?directory=/tmp/cache&timeout=1&shards=0")  # disable shards
Gb = 1073741824
cache.setup("disk://", size_limit=3 * Gb, shards=12)
```

### Basic API

There are few basic methods to work with cache:

```python
from cashews import cache

cache.setup("mem://")  # configure as in-memory cache

await cache.set(key="key", value=90, expire=60, exist=None)  # -> bool
await cache.set_raw(key="key", value="str")  # -> bool
await cache.get("key", default=None)  # -> Any
await cache.get_raw("key")
await cache.get_many("key1", "key2", default=None)
await cache.incr("key") # -> int
await cache.delete("key")
await cache.delete_match("pattern:*")
async for key in cache.scan("pattern:*"):
    ...
async for key, value in cache.get_match("pattern:*", batch_size=100, default=None):
    ...

await cache.expire("key", timeout=10)
await cache.get_expire("key")  # -> int seconds to expire
await cache.ping(message=None)  # -> bytes
await cache.clear()
await cache.is_locked("key", wait=60)  # -> bool
async with cache.lock("key", expire=10):
    ...
await cache.set_lock("key", value="value", expire=60)  # -> bool
await cache.unlock("key", "value")  # -> bool
```

### Strategies

- [Simple cache](#simple-cache)
- [Fail cache (Failover cache)](#fail-cache-failover-cache)
- [Hit cache](#hit-cache)
- [Early](#early)
- [Soft](#soft)
- [Locked](#locked)
- [Rate limit](#rate-limit)
- [Circuit breaker](#circuit-breaker)

#### Simple cache

This is typical cache strategy: execute, store and return from cache until it expired.

```python
from datetime import timedelta

from cashews import cache

@cache(ttl=timedelta(hours=3), key="user:{request.user.uid}")
async def long_running_function(request):
    ...
```

#### Fail cache (Failover cache)

Return cache result, if one of the given exceptions is raised (at least one function
call should be succeed prior that).

```python
from cashews import cache  # or: from cashews import failover

# note: the key will be "__module__.get_status:name:{name}"
@cache.failover(ttl="2h", exceptions=(ValueError, MyException))
async def get_status(name):
    value = await api_call()
    return {"status": value}
```

If exceptions didn't get will catch all exceptions or use default if it set by:

```python
cache.set_default_fail_exceptions(ValueError, MyException)
```

#### Hit cache

Expire cache after given numbers of call `cache_hits`.

```python
from cashews import cache  # or: from cashews import hit

@cache.hit(ttl="2h", cache_hits=100, update_after=2)
async def get(name):
    ...
```

#### Early

Cache strategy that tries to solve [Cache stampede problem](https://en.wikipedia.org/wiki/Cache_stampede)
with a hot cache recalculating result in a background.

```python
from cashews import cache  # or: from cashews import early

# if you call this function after 7 min, cache will be updated in a background
@cache.early(ttl="10m", early_ttl="7m")
async def get(name):
    value = await api_call()
    return {"status": value}
```

#### Soft

Like a simple cache, but with a fail protection base on soft ttl.

```python
from cashews import cache

# if you call this function after 7 min, cache will be updated and return a new result.
# If it fail on recalculation will return current cached value (if it not more then 10 min old)
@cache.soft(ttl="10m", soft_ttl="7m")
async def get(name):
    value = await api_call()
    return {"status": value}
```

#### Locked

Decorator that can help you to solve [Cache stampede problem](https://en.wikipedia.org/wiki/Cache_stampede).
Lock following function calls until the first one will be finished.
This guarantees exactly one function call for given ttl.

> :warning: \*\*Warning: this decorator will not cache the result
> To do so you can combine this decorator with any cache decorator or use parameter `lock=True` with `@cache()`

```python
from cashews import cache  # or: from cashews import locked

@cache.locked(ttl="10m")
async def get(name):
    value = await api_call()
    return {"status": value}
```

#### Rate limit

Rate limit for a function call - do not call a function if rate limit is reached

```python
from cashews import cache  # or: from cashews import rate_limit

# no more than 10 calls per minute or ban for 10 minutes
@cache.rate_limit(limit=10, period=timedelta(minutes=1), ttl=timedelta(minutes=10))
async def get(name):
    return {"status": value}
```

#### Circuit breaker

Circuit breaker

```python
from cashews import cache  # or: from cashews import circuit_breaker

@cache.circuit_breaker(errors_rate=10, period="1m", ttl="5m")
async def get(name):
    ...
```

#### Bloom filter (experimental)

Bloom filter

```python
from cashews import cache

@cache.bloom(name="emails:{email}", capacity=10_000, false_positives=1)
async def email_exists(email):
    ...

for email in all_users_emails:
    await email_exists.set(email)

await email_exists("example@example.com")
```

### Cache condition

By default, any result of function call is stored, even it is a `None`.
Caching decorators have parameter `condition`, that can be:

- a callable object that receive result of function call, args, kwargs and a cache key
- a string: "not_none" or "skip_none" to do not cache `None` values in

```python
from cashews import cache, NOT_NONE

@cache(ttl="1h", condition=NOT_NONE)
async def get():
    ...


def skit_test_result(result, args, kwargs, key=None) -> bool:
    return result != "test"

@cache(ttl="1h", condition=skit_test_result)
async def get():
    ...

```

Also caching decorators have parameter `time_condition` - min latency in seconds (can be set like `ttl` - by string or timedelata object)
for getting result of function call to be cached.

```python
from cashews import cache

@cache(ttl="1h", time_condition="3s")
async def get():
    ...
```

### Template Keys

Often, to compose a key, you need all the parameters of the function call.
By default, Cashews will generate a key using the function name, module names and parameters

```python
from cashews import cache

@cache(ttl=timedelta(hours=3))
async def get_name(user, *args, version="v1", **kwargs):
    ...

# a key template will be "__module__.get_name:user:{user}:{__args__}:version:{version}:{__kwargs__}"

await get_name("me", version="v2")
# a key will be "__module__.get_name:user:me::version:v2"
await get_name("me", version="v1", foo="bar")
# a key will be "__module__.get_name:user:me::version:v1:foo:bar"
await get_name("me", "opt", "attr", opt="opt", attr="attr")
# a key will be "__module__.get_name:user:me:opt:attr:version:v1:attr:attr:opt:opt"
```

The same with a class method

```python
from cashews import cache

class MyClass:

    @cache(ttl="2h")
    async def get_name(self, user, version="v1"):
         ...

# a key template will be "__module__:MyClass.get_name:self:{self}:user:{user}:version:{version}

await MyClass().get_name("me", version="v2")
# a key will be "__module__:MyClass.get_name:self:<__module__.MyClass object at 0x105edd6a0>:user:me:version:v1"
```

As you can see, there is an ugly reference to the instance in the key. That is not what we expect to see.
That cache will not work properly. There are 3 solutions to avoid it.) define `__str__` magic method in our class

```python

class MyClass:

    @cache(ttl="2h")
    async def get_name(self, user, version="v1"):
         ...

    def __str__(self) -> str:
        return self._host

await MyClass(host="http://example.com").get_name("me", version="v2")
# a key will be "__module__:MyClass.get_name:self:http://example.com:user:me:version:v1"
```

2. Set a key template

```python
class MyClass:

    @cache(ttl="2h", key="{self._host}:name:{user}:{version}")
    async def get_name(self, user, version="v1"):
         ...

await MyClass(host="http://example.com").get_name("me", version="v2")
# a key will be "http://example.com:name:me:v1"
```

3. Use `noself` or `noself_cache` if you want to exclude `self` from a key

```python
from cashews import cache, noself, noself_cache

class MyClass:

    @noself(cache)(ttl="2h")
    async def get_name(self, user, version="v1"):
         ...

    @noself_cache(ttl="2h")  # for python <= 3.8
    async def get_name(self, user, version="v1"):
         ...
# a key template will be "__module__:MyClass.get_name:user:{user}:version:{version}

await MyClass().get_name("me", version="v2")
# a key will be "__module__:MyClass.get_name:user:me:version:v1"
```

Sometimes you may need to format the parameters or define your
own template for the key and Cashews allows you to do this:

```python
@cache.failover(key="name:{user.uid}")
async def get_name(user, version="v1"):
    ...

await get_name(user, version="v2")
# a key will be "fail:name:me"

@cache.hit(key="user:{token:jwt(user_name)}", prefix="new")
async def get_name(token):
    ...

await get_name(token)
# a key will be "new:user:alex"

from cashews import default_formatter, cache

@default_formatter.register("upper")
def _upper(value):
    return value.upper()

@default_formatter.type_format(Decimal)
def _decimal(value: Decimal) -> str:
    return value.quantize(Decimal("0.00"))


@cache(key="price-{item.price}:{item.currency:upper}")
async def get_price(item):
    ...

await get_name(item)
# a key will be "price-10.00:USD"
```

### Cache invalidation

Cache invalidation - one of the main Computer Science well known problem.
That's why `ttl` is a required parameter for all cache decorators.

Sometimes, you want to invalidate cache after some action is triggered.
Consider this example:

```python
from datetime import timedelta

from cashews import cache

@cache(ttl=timedelta(days=1))
async def user_items(user_id, fresh=False):
    ...

@cache(ttl=timedelta(hours=3))
async def items(page=1):
    ...

@cache.invalidate("module:items:page:*")  # or: @cache.invalidate(items)
@cache.invalidate(user_items, {"user_id": lambda user: user.id}, defaults={"fresh": True})
async def create_item(user):
   ...
```

Here, cache for `user_items` and `items` will be invalidated every time `create_item` is called.

#### Cache invalidation on code change

Often, you may face a problem with invalid cache after code is changed. For example:

```python
@cache(ttl=timedelta(days=1), key="user:{user_id}")
async def get_user(user_id):
    return {"name": "Dmitry", "surname": "Krykov"}
```

Then, returned value was changed to:

```bash
-    return {"name": "Dmitry", "surname": "Krykov"}
+    return {"full_name": "Dmitry Krykov"}
```

Since function returning a dict, there is no way simple way to automatically detect
that kind of cache invalidity

One way to solve the problem is to add a prefix for this cache:

```python
@cache(ttl=timedelta(days=1), prefix="v2")
async def get_user(user_id):
    return {"full_name": "Dmitry Krykov"}
```

but it is so easy to forget to do it...

The best defense against this problem is to use your own datacontainers, like
[dataclasses](https://docs.python.org/3/library/dataclasses.html),
with defined `__repr__` method.
This will add distinctness and `cashews` can detect changes in such structures automatically
by checking [object representation](https://docs.python.org/3/reference/datamodel.html#object.__repr__).

```python
from dataclasses import dataclass

from cashews import cache

@dataclass
class User:
    name: str
    surname: str

# or define your own class with __repr__ method

class User:

    def __init__(self, name, surname):
        self.name, self.surname = name, surname

    def __repr__(self):
        return f"{self.name} {self.surname}"

# Will detect changes of a structure
@cache(ttl=timedelta(days=1), prefix="v2")
async def get_user(user_id):
    return User("Dima", "Krykov")
```

### Detect the source of a result

Decorators give us a very simple API but also make it difficult to understand where
result is coming from - cache or direct call.

To solve this problem `cashews` has `context_cache_detect` context manager:

```python
from cashews import context_cache_detect

with context_cache_detect as detector:
    response = await decorated_function()
    keys = detector.get()
print(keys)
# >>> {"my:key": [{"ttl": 10, "name": "simple", "backend": "redis"}, ], "fail:key": [{"ttl": timedelta(hours=10), "exc": RateLimit}, "name": "fail", "backend": "mem"],}
```

or you can use `CacheDetect` class:

```python
from cashews import CacheDetect

cache_detect = CacheDetect()
await func(_from_cache=cache_detect)
assert cache_detect.keys == {}

await func(_from_cache=cache_detect)
assert len(cache_detect.keys) == 1
```

A simple middleware to use it in a web app:

```python
@app.middleware("http")
async def add_from_cache_headers(request: Request, call_next):
    with context_cache_detect as detector:
        response = await call_next(request)
        if detector.keys:
            key = list(detector.keys.keys())[0]
            response.headers["X-From-Cache"] = key
            expire = await cache.get_expire(key)
            response.headers["X-From-Cache-Expire-In-Seconds"] = str(expire)
            if "exc" in detector.keys[key]:
                response.headers["X-From-Cache-Exc"] = str(detector.keys[key]["exc"])
    return response
```

### Middleware

Cashews provide the interface for a "middleware" pattern:

```python
import logging
from cashews import cache

logger = logging.getLogger(__name__)


async def logging_middleware(call, *args, backend=None, cmd=None, **kwargs):
    key = args[0] if args else kwargs.get("key", kwargs.get("pattern", ""))
    logger.info("=> Cache request: %s ", cmd, extra={"command": cmd, "cache_key": key})
    return await call(*args, **kwargs)


cache.setup("mem://", middlewares=(logging_middleware, ))
```

## Development

### Setup

- Clone the project.
- After creating a virtual environment, install [pre-commit](https://pre-commit.com/):
  ```shell
  pip install pre-commit && pre-commit install --install-hooks
  ```

### Tests

To run tests you can use `tox`:

```shell
pip install tox
tox -e py  // tests for inmemory backend
tox -e py-diskcache  // tests for diskcache backend
tox -e py-redis  // tests for redis backend  - you need to run redis
tox -e py-integration  // tests for integrations with aiohttp and fastapi

tox // to run all tests for all python that is installed on your machine
```

Or use `pytest`, but 2 tests always fail, it is OK:

```shell
pip install .[tests,redis,diskcache,speedup] fastapi aiohttp requests

pytest // run all tests with all backends
pytest -m "not redis" // all tests without tests for redis backend
```
