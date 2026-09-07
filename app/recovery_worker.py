"""Native parser boundary with a parent-enforced timeout."""

import base64
import json
import sys


def main():
    try:
        # Do not import desktop or semantic packages in this process.
        if sys.platform == "linux":
            import resource

            resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
            resource.setrlimit(resource.RLIMIT_CPU, (45, 45))
            resource.setrlimit(resource.RLIMIT_FSIZE, (30 * 1024**2, 30 * 1024**2))
        request = json.loads(sys.stdin.read(38_000_001))
        raw = base64.b64decode(request["raw"], validate=True)
        from .advanced import process

        response = process(raw, str(request["name"]), bool(request.get("recover")))
    except Exception as exc:
        response = {"error": str(exc)[:500] or "The source could not be processed."}
    print(json.dumps(response))


if __name__ == "__main__":
    main()
