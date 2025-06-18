# WebDeface Monitor Slack Integration Guide

This guide provides comprehensive instructions for setting up and using the WebDeface Monitor Slack integration.

## Table of Contents

1.  [Slack App Setup](#slack-app-setup)
2.  [Slack Commands](#slack-commands)
3.  [Troubleshooting](#troubleshooting)

## Slack App Setup

Follow these steps to create and configure the Slack app for the WebDeface Monitor.

### 1. Create a New Slack App

1.  Go to the [Slack API Dashboard](https://api.slack.com/apps) and click **"Create New App"**.
2.  Select **"From scratch"** and enter the following details:
    *   **App Name:** `WebDeface Monitor`
    *   **Workspace:** Select your target workspace.
3.  Click **"Create App"**.

### 2. Configure OAuth & Permissions

1.  In the sidebar, click **"OAuth & Permissions"**.
2.  Under **"Bot Token Scopes"**, add the following scopes:
    *   `app_mentions:read`
    *   `channels:history`
    *   `channels:read`
    *   `chat:write`
    *   `chat:write.public`
    *   `commands`
    *   `groups:history`
    *   `groups:read`
    *   `im:history`
    *   `im:read`
    *   `im:write`
    *   `users:read`
    *   `users:read.email`

### 3. Enable Socket Mode

1.  In the sidebar, click **"Socket Mode"** and enable it.
2.  Generate an app-level token with the `connections:write` scope.
3.  Save the token (starts with `xapp-`) as `SLACK_APP_TOKEN`.

### 4. Configure Slash Commands

1.  In the sidebar, click **"Slash Commands"** and create a new command:
    *   **Command:** `/webdeface`
    *   **Short Description:** Control and interact with WebDeface Monitor.
    *   **Usage Hint:** `[command] [subcommand] [options]`

### 5. Configure Interactive Components

1.  In the sidebar, click **"Interactivity & Shortcuts"** and enable interactivity.

### 6. Configure Event Subscriptions

1.  In the sidebar, click **"Event Subscriptions"** and enable events.
2.  Under **"Subscribe to bot events"**, add the following events:
    *   `app_mention`
    *   `message.channels`
    *   `message.groups`
    *   `message.im`

### 7. Install App to Workspace

1.  In the sidebar, click **"Install App"** and install the app to your workspace.
2.  Copy the **Bot User OAuth Token** (starts with `xoxb-`) and save it as `SLACK_BOT_TOKEN`.

### 8. Environment Variables

Update your `.env` file with the following:

```bash
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here
```

## Slack Commands

The primary command prefix is `/webdeface`.

### Command Syntax

```
/webdeface <GROUP> <SUBCOMMAND> [ARGUMENTS] [FLAGS]
```

Flags use the format `name:value`. For example, `name:"Example Site"`.

### Website Management

*   `/webdeface website add <URL> [name:TEXT] [interval:NUMBER] [max-depth:NUMBER]`
*   `/webdeface website remove <WEBSITE_ID>`
*   `/webdeface website list [status:CHOICE]`
*   `/webdeface website status <WEBSITE_ID>`

### Monitoring Operations

*   `/webdeface monitoring start [WEBSITE_ID]`
*   `/webdeface monitoring stop [WEBSITE_ID]`
*   `/webdeface monitoring pause <WEBSITE_ID> [duration:NUMBER]`
*   `/webdeface monitoring resume <WEBSITE_ID>`
*   `/webdeface monitoring check <WEBSITE_ID>`

### System Management

*   `/webdeface system status`
*   `/webdeface system health`
*   `/webdeface system metrics [range:TEXT] [type:TEXT]`
*   `/webdeface system logs [level:TEXT] [component:TEXT] [limit:NUMBER] [since:TEXT]`

### Help System

*   `/webdeface help [COMMAND_GROUP]`
*   `/webdeface commands`

## Troubleshooting

If you encounter issues, check the following:

*   Ensure the bot is invited to the channel.
*   Verify that the correct tokens and secrets are in your `.env` file.
*   Check the application logs for any errors.
*   Use `/webdeface help` to see available commands and their syntax.

For further assistance, please open an issue on our [GitHub repository](https://github.com/bcdannyboy/webdeface/issues).