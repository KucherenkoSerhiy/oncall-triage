# M5a decisions

Minimal choices made where the spec left room, for the record.

- **`ESTATE` column position in `bankops tail`**: placed between `SEV` and
  `SERVICE` (`TIME SEV ESTATE SERVICE ALERT STATUS OCC VERDICT`). The spec
  only fixed the column name and width (11), not its position.
- **`ChaosClient` clock injection**: the spec's constructor signature
  (`chaos_url, token, ttl_seconds=60, http=<injectable>`) doesn't list a
  clock parameter, but requirement 5 asks for "TTL caching with an injected
  clock" as a test scenario. Added an optional `clock` keyword
  (`Callable[[], float] = time.monotonic`) so tests can control elapsed time
  without sleeping.
- **`ChaosClient`/`forward` HTTP injection shape**: `ChaosClient`'s `http`
  callable is `(url, headers) -> bytes` (GET only, mirrors
  `cli/bankops/client.request`'s body-return convention); `forward`'s `http`
  callable is `(method, url, headers, body) -> (status, body)` since the
  caller needs the raw ingest status code to decide 202 vs. 502.
- **`ForwardResult.status`**: holds the raw ingest response status (e.g.
  200, 500), not the forwarder's own 202/502. The HTTP trigger
  (`function_app.py`) maps that raw status to 202/502 for its own caller, as
  the spec describes it as something "the trigger" does.
- **`VALID_MODES` location**: extended `bank/aws/common.py`'s `VALID_MODES`
  dict in place (adding `customer-notifications`) rather than introducing a
  new estate-neutral module, since the spec says to "extend, do not
  duplicate" the single source of truth the console API and `bankops chaos`
  already import from there.
