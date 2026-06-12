"""
Multi-process launcher — fans the FastAPI app out across cores.

One uvicorn process per shard means the GIL never becomes the bottleneck.
Each shard is bound to its own port; an upstream load balancer fronts them.
"""
import os
import sys
from multiprocessing import Process
import uvicorn

SHARDS = [
    ("shard-a", 8010),
    ("shard-b", 8011),
    ("shard-c", 8012),
    ("shard-d", 8013),
]


def _serve(shard: str, port: int):
    os.environ["SHARD_ID"] = shard
    uvicorn.run(
        "main_enhanced:app",
        host="0.0.0.0",
        port=port,
        workers=1,
        log_level="info",
    )


def main():
    procs = [Process(target=_serve, args=s) for s in SHARDS]
    for p in procs:
        p.start()
    try:
        for p in procs:
            p.join()
    except KeyboardInterrupt:
        for p in procs:
            p.terminate()
        sys.exit(0)


if __name__ == "__main__":
    main()
