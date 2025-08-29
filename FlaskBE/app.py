import os

from flask import Flask, request, jsonify
from github import Github
from openai import OpenAI
import requests

app = Flask(__name__)

# GitHub + OpenAI clients
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


@app.route('/review', methods=['POST'])
def review():
    data = request.json
    repo_name = data['repo']
    github_token = data['git_token']
    pr_number = data['pr_number']
    openai_key = data['openai_key']
    if openai_key:
        client = OpenAI(
            api_key=f"{openai_key}")
    else:
        client = OpenAI(
        api_key=f"{OPENAI_API_KEY}")
    gh = Github(github_token)
    repo = gh.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    # Collect PR data
    pr_content = f"PR Title: {pr.title}\nDescription: {pr.body}\n\n"
    file_map = {}  # store files and commit SHA for later

    for file in pr.get_files():
        pr_content += f"\nFile: {file.filename}\nDiff:\n{file.patch}\n"
        file_map[file.filename] = {
            "commit_id": pr.head.sha,  # latest commit SHA
            "filename": file.filename
        }

    # Send to AI and ask for inline comments
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": (
                    "Review this PR and return inline comments in JSON format like:\n"
                    '[{"file":"path/file.py","line":42,"comment":"Your feedback"}]'
                    f"\n\nPR Details:\n{pr_content}"
                )
            }
        ]
    )

    ai_output = response.choices[0].message.content.strip()

    # Try parsing AI response as JSON
    import re, json

    # Remove ```json ... ``` wrappers if present
    clean_output = re.sub(r"^```(json)?|```$", "", ai_output, flags=re.MULTILINE).strip()

    try:
        comments = json.loads(clean_output)
    except Exception as e:
        return jsonify({
            "review": ai_output,
            "note": f"AI output not valid JSON ({e}). Showing raw output."
        })

    # Post comments back to GitHub
    headers = {"Authorization": f"token {github_token}"}
    comment_url = f"https://api.github.com/repos/{repo_name}/pulls/{pr_number}/comments"
    for file in pr.get_files():
        print(file.filename, file.patch)
    posted_comments = []
    for c in comments:
        try:
            file_info = file_map.get(c["file"])
            if not file_info:
                continue

            payload = {
                "body": c["comment"],
                "commit_id": file_info["commit_id"],
                "path": c["file"],
                "side": "RIGHT",
                "line": c["line"]
            }
            r = requests.post(comment_url, headers=headers, json=payload)
            print("Response:", r.status_code, r.json())
            if r.status_code == 201:
                posted_comments.append(c)
        except Exception as e:
            print("Error posting comment:", e)

    return jsonify({
        "review": "Inline comments posted successfully",
        "comments": posted_comments
    })

if __name__ == '__main__':
    app.run(debug=True)
