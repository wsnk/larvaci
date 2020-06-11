import os
import json
import logging
import aiohttp


GITHUB_API_URL="https://api.github.com/graphql"


class GitHubClient:
    def __init__(self, token, logger=None):
        self.logger = logger or logging.getLogger()
        self.headers = {
            "Authorization": f"bearer {token}"
        }

    async def request(self, query):
        data = json.dumps(query).encode("utf-8")
        self.logger.debug(f"Make GitHub API request: {data} ...")
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.post(GITHUB_API_URL, data=data) as response:
                result = await response.json()
                self.logger.debug(f"GitHub API response: {result}")
                return result


# -------------------------------------------------------------------------------------------------


def pull_requests(repo_owner, repo_name, states=None):
    query = """query($repo_owner:String!, $repo_name:String!) {
        repository(owner: $repo_owner, name: $repo_name) {
            id,
            sshUrl,
            pullRequests(last: 10) {
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
            "repo_name": repo_name
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
