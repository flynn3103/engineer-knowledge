# Content Delivery Networks

> Control which responses are cached, where they are served, and how stale or unsafe content is removed.

## Topics

| # | Topic | Practice outcome |
|---|---|---|
| 01 | [Pull CDN](01-pull-cdn/junior.md) | Trace a miss, origin fill, and later hit. |
| 02 | [Push CDN](02-push-cdn/junior.md) | Decide when explicit publication is worth the workflow. |
| 03 | [Cache Invalidation](03-cache-invalidation/junior.md) | Design versioning and purge recovery. |
| 04 | [Edge Locations](04-edge-locations/junior.md) | Measure user-to-edge and edge-to-origin paths. |
| 05 | [CDN Security](05-cdn-security/junior.md) | Protect origins, keys, and cache boundaries. |

## Practice loop

Request the same object twice, compare cache headers and timing, then change one cache-key input and explain why the result should hit or miss.
