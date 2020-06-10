import os
import json
import logging
import urllib.request
import aiohttp


GITHUB_API_URL="https://api.github.com/graphql"


async def github_request(query):
    token = os.environ.get("GITHUB_ACCESS_TOKEN")
    data = json.dumps(query).encode("utf-8")
    headers = {
        "Authorization": f"bearer {token}"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(GITHUB_API_URL, data=data) as resp:
            return await resp.json()


def request(query):
    token = os.environ.get("GITHUB_ACCESS_TOKEN")
    data = json.dumps(query).encode("utf-8")

    resp = urllib.request.urlopen(
        urllib.request.Request(
            url=GITHUB_API_URL,
            headers={
                "Authorization": f"bearer {token}"
            },
            method="POST",
            data=data
        )
    )
    return json.loads(resp.read())
