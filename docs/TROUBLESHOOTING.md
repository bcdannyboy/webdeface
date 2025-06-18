# Troubleshooting Guide

This guide provides solutions to common issues you may encounter while using the WebDeface Monitor.

## Common Issues

### Service Won't Start

**Symptoms:**
*   Connection refused errors when accessing the API.
*   The application process exits immediately after starting.

**Solutions:**
1.  **Port already in use:** Check if another application is using the same port. You can change the port by setting the `PORT` environment variable.
2.  **Missing environment variables:** Ensure that all required environment variables are set. Refer to the [Configuration](CONFIGURATION.md) guide for a list of required variables.
3.  **Database issues:** Check the database connection and ensure that the database is running.

### Monitoring Jobs Not Running

**Symptoms:**
*   Websites are not being checked.
*   No new scan results are being generated.

**Solutions:**
1.  **Scheduler not started:** Ensure that the monitoring scheduler is running.
2.  **Invalid cron expressions:** Check the cron expressions for your websites to ensure they are valid.

### Classification Not Working

**Symptoms:**
*   All changes are classified as "unknown".
*   Errors related to the Claude API.

**Solutions:**
1.  **Invalid API key:** Ensure that your Claude API key is correct and has not expired.
2.  **Rate limiting:** Check if you are exceeding the rate limits for the Claude API.

### Slack Notifications Not Working

**Symptoms:**
*   No Slack messages are received for alerts.
*   Errors related to the Slack API.

**Solutions:**
1.  **Invalid bot token:** Ensure that your Slack bot token is correct.
2.  **Missing bot permissions:** Check that the bot has the required permissions to post in the specified channels.
3.  **Channel access issues:** Ensure that the bot has been invited to the channels where you want to receive notifications.

## Logging & Debugging

To enable debug logging, set the `LOG_LEVEL` environment variable to `DEBUG`. This will provide more detailed information in the logs, which can be helpful for troubleshooting.

The logs are located in the `data/` directory. You can view the logs using the following command:

```bash
tail -f data/webdeface.log
```

## Support

If you are still unable to resolve the issue, please open an issue on our [GitHub repository](https://github.com/bcdannyboy/webdeface/issues). Please include the following information in your issue report:

*   A description of the issue.
*   Steps to reproduce the issue.
*   The relevant logs.
*   Your configuration (with any sensitive information removed).
