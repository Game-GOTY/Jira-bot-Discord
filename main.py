from flask import Flask, request
import requests
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

app = Flask(__name__)

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")


# New GET route for testing or status
@app.route("/", methods=["GET"])
def webhook_status():
    if not DISCORD_WEBHOOK_URL:
        return "DISCORD_WEBHOOK_URL not set in environment", 500
    return "Webhook server is running!", 200


@app.route("/webhook", methods=["POST"])
def jira_webhook():
    if not DISCORD_WEBHOOK_URL:
        return "DISCORD_WEBHOOK_URL not set in environment", 500

    # Token validation
    jira_token = os.environ.get("JIRA_SECRET_TOKEN")
    if jira_token and "X-Jira-Webhook-Token" in request.headers:
        received_token = request.headers.get("X-Jira-Webhook-Token", "")
        if received_token != jira_token:
            print(f"Jira Token mismatch")
            return "Invalid token", 403

    # Handle empty or non-JSON requests
    if not request.content_type or request.content_length == 0:
        query_user = request.args.get("triggeredByUser", "Unknown")
        message = (
            f"Webhook ping or empty request received. Triggered by user: {query_user}"
        )
        response = requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
        if response.status_code == 204:
            return "Success (empty request handled)", 200
        else:
            return f"Failed to send to Discord: {response.text}", 500

    # Try to parse JSON payload
    try:
        data = request.json
        if (
            data["issue"]["fields"]["project"]["id"] == "10005"
            and data["issue"]["fields"]["project"]["name"] == "GOTY"
        ):
            issue_key = data["issue"]["key"]
            issue_summary = data["issue"]["fields"]["summary"]
            event_type = data["webhookEvent"].split(":")[1]
            status = data["issue"]["fields"]["status"]["name"]
            user = data["user"]["displayName"]
            time_zone_str = data["user"]["timeZone"]
            time = (
                datetime.fromtimestamp(data["timestamp"] / 1000, timezone.utc)
                .astimezone(ZoneInfo(time_zone_str))
                .strftime("%Y-%m-%d %H:%M:%S")
            )
            if event_type == "issue_created" or event_type == "issue_deleted":
                message = f"**{issue_key}** - **{event_type}**: **{issue_summary}** by **{user}** at {time}.\nURL: https://goty.atlassian.net/browse/{issue_key}/"
            else:
                message = f"**{issue_key}** - Status changed: **{status}** for **{issue_summary}** by **{user}** at {time}.\nURL: https://goty.atlassian.net/browse/{issue_key}/"
            response = requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
            if response.status_code == 204:
                return "Success", 200
            else:
                return f"Failed to send to Discord: {response.text}", 500
        else:
            return "Not Dev table. ignored!"
    except Exception as e:
        print(f"Error: {e}")
        return "Invalid payload", 415
