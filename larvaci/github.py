import os
import json
import logging
import aiohttp
import asyncio


GITHUB_API_URL="https://api.github.com/graphql"


class GitHubClient:
    def __init__(self, token, logger=None):
        self.logger = logger or logging.getLogger()
        self.headers = {
            "Authorization": f"bearer {token}"
        }

    async def request(self, query, attempts=3):
        data = json.dumps(query).encode("utf-8")
        self.logger.debug(f"Make GitHub API request: {data} ...")
        async with aiohttp.ClientSession(headers=self.headers) as session:
            while True:
                try:
                    async with session.post(GITHUB_API_URL, data=data) as response:
                        result = await response.json()
                        self.logger.debug(f"GitHub API response: {result}")
                        return result
                except:
                    if attempts == 0:
                        raise
                    self.logger.exception(f"Request to GitHb API failed, retry...")
                    attempts -= 1
                    await asyncio.sleep(1)

    async def add_comment(self, subject_id, content):
        try:
            resp = await self.request(add_comment(subject_id=subject_id, content=content))
            return resp["data"]["addComment"]["commentEdge"]["node"]["id"]
        except Exception:
            self.logger.exception(f"Failed to add GitHub comment")
            return None

    async def update_comment(self, comment_id, content):
        try:
            await self.request(update_comment(comment_id=comment_id, content=content))
        except Exception:
            self.logger.exception(f"Failed to add GitHub comment")


# -------------------------------------------------------------------------------------------------

class PullRequestState:
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    MERGED = "MERGED"


def pull_requests(repo_owner, repo_name, **kwargs):

    query = """query($repo_owner:String!, $repo_name:String!, $states:[PullRequestState!], $after:String) {
        repository(owner: $repo_owner, name: $repo_name) {
            id, url, sshUrl,
            pullRequests(last: 100, states: $states, after: $after) {
                edges {
                    cursor,
                    node {
                        id,
                        title,
                        state,
                        createdAt,
                        baseRefName, baseRefOid,
                        headRefName, headRefOid
                    }
                }
            }
        }
    }"""

    return {
        "query": query,
        "variables": {
            "repo_owner": repo_owner,
            "repo_name": repo_name,
            **kwargs
        }
    }


def add_comment(subject_id, content):
    query = """mutation ($subject_id:ID!, $content:String!) {
        addComment(input: {
            subjectId: $subject_id,
            body: $content
        }) {
            commentEdge { cursor, node { id } }
        }
    }"""
    
    return {
        "query": query,
        "variables": {
            "subject_id": subject_id,
            "content": content
        }
    }


def update_comment(comment_id, content):
    query = """mutation ($comment_id:ID!, $content:String!) {
        updateIssueComment(input: {
            id: $comment_id,
            body: $content
        }) {
            issueComment { id }
        }
    }"""
    
    return {
        "query": query,
        "variables": {
            "comment_id": comment_id,
            "content": content
        }
    }


# -------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    import asyncio
    import logging

    parser = argparse.ArgumentParser()
    parser.add_argument("--token", help="GitHub acces token", type=str)

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)
    
    client = GitHubClient(token=args.token)
    # response = asyncio.run(client.request(pull_requests("hisicam-buildbot", "x")))

    xid = "MDExOlB1bGxSZXF1ZXN0NDMxNTczOTQz"

    response = asyncio.run(client.request(add_comment(subject_id=xid, content="a-a-a-a-a!")))
    print(json.dumps(response, indent=2))
