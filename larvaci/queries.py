from . import github_request


async def pull_requests(repo_owner, repo_name, states=None):
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

    variables = {
        "repo_owner": repo_owner,
        "repo_name": repo_name,
    }

    return await github_request({
        "query": query,
        "variables": variables
    })
