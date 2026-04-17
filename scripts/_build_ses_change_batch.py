import json
import os
import sys

domain = os.environ["DOMAIN"]
region = os.environ["REGION"]

identity = json.load(sys.stdin)
tokens = identity["DkimAttributes"]["Tokens"]
if len(tokens) != 3:
    raise SystemExit(f"expected 3 DKIM tokens, got {len(tokens)}")

changes = []

for token in tokens:
    changes.append(
        {
            "Action": "UPSERT",
            "ResourceRecordSet": {
                "Name": f"{token}._domainkey.{domain}",
                "Type": "CNAME",
                "TTL": 1800,
                "ResourceRecords": [{"Value": f"{token}.dkim.amazonses.com"}],
            },
        }
    )

changes.append(
    {
        "Action": "UPSERT",
        "ResourceRecordSet": {
            "Name": domain,
            "Type": "MX",
            "TTL": 1800,
            "ResourceRecords": [
                {"Value": f"10 inbound-smtp.{region}.amazonaws.com"}
            ],
        },
    }
)

batch = {
    "Comment": f"SES DKIM + inbound MX for {domain}",
    "Changes": changes,
}

print(json.dumps(batch))
