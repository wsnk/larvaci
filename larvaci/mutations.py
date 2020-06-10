import json
from . import github_request


async def add_comment(subject_id, content):
    query = """mutation ($subject_id:ID!, $content:String!) {
        addComment(input: {
            subjectId: $subject_id,
            body: $content
        }) {
            commentEdge { cursor, node { id } }
        }
    }"""
    
    return await github_request({
        "query": query,
        "variables": {
            "subject_id": subject_id,
            "content": content
        }
    })


async def update_comment(comment_id, content):
    query = """mutation ($comment_id:ID!, $content:String!) {
        updateIssueComment(input: {
            id: $comment_id,
            body: $content
        }) {
            issueComment { id }
        }
    }"""
    
    return await github_request({
        "query": query,
        "variables": {
            "comment_id": comment_id,
            "content": content
        }
    })
