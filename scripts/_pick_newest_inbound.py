"""Print the newest object key under emails/ in the inbound S3 bucket.

Optional arg: a since-iso8601-timestamp; prints the newest key whose
LastModified is >= that time, or exits non-zero if there isn't one yet.
"""

import sys
from datetime import datetime, timezone

import boto3

BUCKET = "cyndibot-incoming-emails"
PREFIX = "emails/"


def main() -> None:
    since = None
    if len(sys.argv) > 1:
        since = datetime.fromisoformat(sys.argv[1])
        if since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)

    s3 = boto3.client("s3")
    resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=PREFIX)
    objs = sorted(
        resp.get("Contents") or [], key=lambda o: o["LastModified"], reverse=True
    )
    if not objs:
        raise SystemExit("no inbound emails yet")

    if since is not None:
        objs = [o for o in objs if o["LastModified"] >= since]
        if not objs:
            raise SystemExit(f"no inbound emails since {since.isoformat()}")

    print(objs[0]["Key"])


if __name__ == "__main__":
    main()
