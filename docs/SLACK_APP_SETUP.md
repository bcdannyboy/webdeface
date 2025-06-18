# Slack App Setup Guide for WebDeface Monitor

**Last Updated:** June 18, 2025

This guide provides detailed, step-by-step instructions for setting up the Slack app portion of the WebDeface Monitor application. Follow these instructions carefully to ensure proper configuration and permissions.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Create a New Slack App](#create-a-new-slack-app)
3. [Configure OAuth & Permissions](#configure-oauth--permissions)
4. [Enable Socket Mode](#enable-socket-mode)
5. [Configure Slash Commands](#configure-slash-commands)
6. [Configure Interactive Components](#configure-interactive-components)
7. [Configure Event Subscriptions](#configure-event-subscriptions)
8. [Install App to Workspace](#install-app-to-workspace)
9. [Environment Variables Setup](#environment-variables-setup)
10. [Testing Your Configuration](#testing-your-configuration)
11. [Troubleshooting](#troubleshooting)

## Prerequisites

Before starting, ensure you have:

- Admin access to a Slack workspace
- Access to your WebDeface Monitor deployment environment
- A secure location to store API tokens and secrets

## Create a New Slack App

1. **Navigate to Slack API Dashboard**
   - Go to [https://api.slack.com/apps](https://api.slack.com/apps)
   - Click the **"Create New App"** button

2. **Choose App Creation Method**
   - Select **"From scratch"**
   - Enter the following details:
     - **App Name:** `WebDeface Monitor`
     - **Pick a workspace:** Select your target workspace
   - Click **"Create App"**

3. **Basic Information**
   - Once created, you'll be redirected to the app configuration page
   - Note down the **Signing Secret** from the "App Credentials" section
   - You'll need this as `SLACK_SIGNING_SECRET` later

## Configure OAuth & Permissions

1. **Navigate to OAuth & Permissions**
   - In the left sidebar, click **"OAuth & Permissions"**

2. **Configure Bot Token Scopes**
   - Scroll down to **"Scopes"** section
   - Under **"Bot Token Scopes"**, add the following OAuth scopes:

   **Required Scopes:**
   ```
   app_mentions:read       - View messages that directly mention @webdeface-monitor
   channels:history        - View messages and other content in public channels
   channels:read           - View basic information about public channels
   chat:write              - Send messages as @webdeface-monitor
   chat:write.public       - Send messages to channels @webdeface-monitor isn't a member of
   commands                - Add shortcuts and/or slash commands
   groups:history          - View messages and other content in private channels
   groups:read             - View basic information about private channels
   im:history              - View messages and other content in direct messages
   im:read                 - View basic information about direct messages
   im:write                - Start direct messages with people
   users:read              - View people in the workspace
   users:read.email        - View email addresses of people in the workspace
   ```

3. **Configure User Token Scopes (Optional)**
   - If you need user-level permissions, add appropriate user token scopes
   - For basic operation, bot token scopes are sufficient

## Enable Socket Mode

Socket Mode allows your app to receive events and commands without exposing a public HTTP endpoint.

1. **Navigate to Socket Mode**
   - In the left sidebar, click **"Socket Mode"**
   - Toggle **"Enable Socket Mode"** to ON

2. **Generate App-Level Token**
   - Click **"Generate Token and Scopes"**
   - Token Name: `websocket-token`
   - Add scope: `connections:write`
   - Click **"Generate"**
   - Copy the token that starts with `xapp-`
   - Save this as `SLACK_APP_TOKEN`

## Configure Slash Commands

1. **Navigate to Slash Commands**
   - In the left sidebar, click **"Slash Commands"**
   - Click **"Create New Command"**

2. **Create /webdeface Command**
   - Configure the following:
     ```
     Command: /webdeface
     Request URL: [Leave empty - Socket Mode handles this]
     Short Description: Control and interact with WebDeface Monitor
     Usage Hint: [command] [subcommand] [options]
     ```
   - Click **"Save"**

3. **Create Legacy Commands (Optional)**
   - If migrating from an older system, you may also want to create:
     - `/status` - Check system status
     - `/alerts` - View recent alerts
     - `/sites` - List monitored websites

## Configure Interactive Components

1. **Navigate to Interactivity & Shortcuts**
   - In the left sidebar, click **"Interactivity & Shortcuts"**
   - Toggle **"Interactivity"** to ON

2. **Configure Request URL**
   - Since you're using Socket Mode, leave the Request URL empty
   - The Socket Mode connection will handle all interactions

3. **Configure Options (Optional)**
   - Select menus: Enable if using dynamic dropdowns
   - Home tab: Enable if implementing app home functionality

## Configure Event Subscriptions

1. **Navigate to Event Subscriptions**
   - In the left sidebar, click **"Event Subscriptions"**
   - Toggle **"Enable Events"** to ON

2. **Configure Request URL**
   - Since you're using Socket Mode, leave this empty

3. **Subscribe to Bot Events**
   - Click **"Subscribe to bot events"**
   - Add the following events:
     ```
     app_mention         - Subscribe to messages mentioning the bot
     message.channels    - Subscribe to messages in public channels
     message.groups      - Subscribe to messages in private channels
     message.im          - Subscribe to direct messages
     ```

4. **Save Changes**
   - Click **"Save Changes"** at the bottom

## Install App to Workspace

1. **Navigate to Install App**
   - In the left sidebar, click **"Install App"**
   - Click **"Install to Workspace"**

2. **Review Permissions**
   - Review the permissions requested
   - Click **"Allow"** to grant permissions

3. **Copy Bot Token**
   - After installation, you'll see the **Bot User OAuth Token**
   - Copy the token that starts with `xoxb-`
   - Save this as `SLACK_BOT_TOKEN`

## Environment Variables Setup

Create or update your `.env` file with the following Slack configuration:

```bash
# Slack Configuration (Required)
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here

# Optional: Restrict access to specific users
SLACK_ALLOWED_USERS=U1234567890,U0987654321

# Optional: Default channels for notifications
SLACK_DEFAULT_CHANNEL=#monitoring
SLACK_ALERT_CHANNEL=#security-alerts
```

## Testing Your Configuration

1. **Start WebDeface Monitor**
   ```bash
   ./run_infrastructure.sh start
   ```

2. **Check Slack Connection**
   - In your Slack workspace, go to any channel
   - Type `/webdeface help`
   - You should see a response with available commands

3. **Test Bot Permissions**
   - Invite the bot to a channel: `/invite @webdeface-monitor`
   - Try sending a test notification
   - Mention the bot: `@webdeface-monitor status`

4. **Verify Socket Mode Connection**
   - Check application logs for Socket Mode connection status
   - Look for: "Slack app in socket mode started successfully"

## Troubleshooting

### Common Issues and Solutions

1. **"not_authed" Error**
   - Verify `SLACK_BOT_TOKEN` is correctly set
   - Ensure the token starts with `xoxb-`
   - Check that the app is installed to your workspace

2. **"invalid_auth" Error**
   - Regenerate your bot token
   - Ensure you're using the bot token, not the app token
   - Verify the token hasn't been revoked

3. **Socket Mode Not Connecting**
   - Verify `SLACK_APP_TOKEN` is correctly set
   - Ensure the token starts with `xapp-`
   - Check that Socket Mode is enabled in your app settings
   - Verify the app-level token has `connections:write` scope

4. **Commands Not Working**
   - Ensure slash commands are configured correctly
   - Verify Socket Mode is enabled
   - Check that the bot has necessary permissions
   - Look for errors in the application logs

5. **Bot Can't Send Messages**
   - Verify the bot has `chat:write` scope
   - For public channels: Ensure `chat:write.public` scope is added
   - For private channels: Bot must be invited to the channel

### Debug Mode

Enable debug logging to troubleshoot issues:

```bash
# In your .env file
LOG_LEVEL=DEBUG
SLACK_DEBUG=true
```

### Testing API Connection

Test your Slack API connection directly:

```bash
# Test bot token
curl -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
     https://slack.com/api/auth.test

# Test app token (Socket Mode)
curl -H "Authorization: Bearer $SLACK_APP_TOKEN" \
     https://slack.com/api/apps.connections.open
```

## Security Best Practices

1. **Token Storage**
   - Never commit tokens to version control
   - Use environment variables or secure secret management
   - Rotate tokens regularly

2. **User Restrictions**
   - Use `SLACK_ALLOWED_USERS` to restrict access
   - Implement role-based permissions in the app
   - Audit user access regularly

3. **Channel Restrictions**
   - Limit bot access to necessary channels only
   - Use private channels for sensitive alerts
   - Configure appropriate channel routing

4. **Webhook Security**
   - Always verify requests using the signing secret
   - Implement request timestamp validation
   - Use HTTPS for all communications

## Next Steps

After completing this setup:

1. Configure monitoring sites via Slack commands
2. Set up alert routing and notifications
3. Customize notification templates
4. Configure user permissions and roles
5. Test the full monitoring workflow

For more information, refer to:
- [Slack API Documentation](https://api.slack.com/docs)
- [WebDeface Monitor Documentation](../README.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)