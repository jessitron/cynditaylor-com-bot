"""Print From / To / Subject / Date for a given S3 inbound key (or the newest)."""

import email
import sys
from email import policy

import boto3

BUCKET = "cyndibot-incoming-emails"
PREFIX = "emails/"


def main() -> None:
    if len(sys.argv) > 1:
        key = sys.argv[1]
    else:
        s3 = boto3.client("s3")
        resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=PREFIX)
        objs = sorted(
            resp.get("Contents") or [],
            key=lambda o: o["LastModified"],
            reverse=True,
        )
        if not objs:
            raise SystemExit("no inbound emails yet")
        key = objs[0]["Key"]

    s3 = boto3.client("s3")
    raw = s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()
    msg = email.message_from_bytes(raw, policy=policy.default)

    print(f"key:     {key}")
    print(f"from:    {msg.get('from')}")
    print(f"to:      {msg.get('to')}")
    print(f"subject: {msg.get('subject')}")
    print(f"date:    {msg.get('date')}")


if __name__ == "__main__":
    main()
