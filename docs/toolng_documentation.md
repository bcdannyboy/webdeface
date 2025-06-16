# Web Defacement Monitor – Comprehensive Documentation

This document provides detailed guidance and code examples for the key libraries and components used in the Web Defacement Monitor tool. It covers usage patterns, authentication, and API references for each major part of the system, as of **June 2025**. The sections below are:

* **Claude Messages API** (Anthropic’s LLM API)
* **Slack Bolt for Python (Async)** (for Slack app integration)
* **Playwright for Python** (headless Chromium browsing)
* **Qdrant (Vector Database)** (for storing and querying embeddings)
* **APScheduler** (scheduling periodic jobs)
* **SQLite via SQLAlchemy** (storing scan data and hashes)

Each section includes best practices, code snippets, and references to official documentation. Use these as a reference to implement or understand the Web Defacement Monitor’s components without needing external lookup.

## Claude Messages API (Anthropic)

Claude is an AI assistant by Anthropic. The Claude **Messages API** allows programmatic interaction with Claude via REST or SDK, supporting structured chat conversations and streaming responses. Below we outline how to authenticate to the API, format messages (system vs user vs assistant roles), construct requests, handle token limits, and utilize streaming “delta” updates.

### API Authentication and Setup

* **API Key**: Obtain an API key from Anthropic’s console. Authenticate by including it in an HTTP header: `x-api-key: <YOUR_API_KEY>`.
* **API Version**: Anthropic requires a version header. For example, use `anthropic-version: 2023-06-01` (the current stable version) in all requests.
* **Endpoint**: The base endpoint for Claude’s message API is `https://api.anthropic.com/v1/messages`. You will POST JSON to this endpoint with your query.

**Example (cURL)** – authenticating and sending a basic prompt:

```bash
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d '{
        "model": "claude-3-7-sonnet-20250219",
        "max_tokens": 1024,
        "messages": [
          {"role": "user", "content": "Hello, world"}
        ]
      }'
```

In this example, we specify the model (Claude version), maximum tokens to generate, and a list of message objects. The API key and version are provided in headers.

### Message Structure and Roles

Claude’s API expects a conversation formatted as a list of messages, each with a `role` and `content`:

* **`role`:** Either `"user"` or `"assistant"`. The conversation should alternate between user and assistant turns. (Anthropic’s API does **not** use a `"system"` role in this list.)
* **`content`:** The text content of the message. This can be a simple string or an array of structured content blocks (for text, code, images, etc.). For basic usage, just supply a string.

Typically, you include the conversation history: for example, a user message, then optionally an assistant reply, then another user message, etc. Claude will then produce the next assistant response based on this context.

**System Prompts:** Instead of a system message in the list, Anthropic provides a top-level `"system"` parameter for instructions or role. This is a single prompt that sets context or behavior for Claude. Use it to prime Claude with background info or a “persona”. For instance, `system: "You are a security analyst assisting with website monitoring."`

**Example – Multiple-turn conversation:**

```json
{
  "model": "claude-3-7-sonnet-20250219",
  "max_tokens": 500,
  "system": "You are a seasoned security analyst.",
  "messages": [
      {"role": "user", "content": "Hello there."},
      {"role": "assistant", "content": "Hi, I'm Claude. How can I help you?"},
      {"role": "user", "content": "How do I detect if a website is defaced?"}
  ]
}
```

Here we set a system role and provide prior turns. Claude will generate the next assistant answer. (The system prompt gives Claude a role – it’s recommended to use it for better context and tone.)

**Content blocks:** The API supports advanced content types (e.g. `{"type": "image", "data": "...base64..."}`), but for most text interactions a simple string is sufficient.

### Example API Call (Python SDK and REST)

Anthropic offers an official Python SDK (`anthropic` package) for convenience. Below are examples using the SDK, including streaming:

**Synchronous request example:**

```python
import anthropic

client = anthropic.Anthropic(api_key="YOUR_API_KEY")
response = client.messages.create(
    model="claude-3-7-sonnet-20250219",
    max_tokens=2048,
    system="You are a seasoned data scientist at a Fortune 500 company.",  # system role
    messages=[ {"role": "user", "content": "Analyze this dataset for anomalies: <dataset>...</dataset>"} ]
)
print(response.content)
```

In this example, we instantiate the client with our API key and call `messages.create()` with the model name, a system prompt, and a user message. The response object’s `content` will contain Claude’s answer text.

**Streaming response (deltas):** To receive Claude’s reply incrementally (token-by-token), set `stream=True` in the API call. The SDK provides a context manager for this:

```python
with client.messages.stream(
    model="claude-opus-4-20250514",
    messages=[ {"role": "user", "content": "Hello"} ],
    max_tokens=1024,
    stream=True
) as stream:
    for partial in stream.text_stream:
        print(partial, end="", flush=True)
```

This will print Claude’s response as it streams in. Internally, the API uses Server-Sent Events (SSE) to send chunks (often called “deltas”). Each event can be a `content_block_delta` or `message_delta` etc., which you concatenate to get the full reply. Using streaming is recommended for responsiveness (e.g., updating a Slack message as Claude generates the answer).

### Token Limits and Best Practices

* **Context Window:** Claude’s models support very large context windows (on the order of 100k to 200k tokens). This means you can include extensive website content or logs in the prompt. However, keep the conversation relevant; extraneous content can still confuse the model.
* **Max Tokens:** The `max_tokens` parameter controls the **output** token limit (how many tokens Claude can generate). Different models have different limits for this; e.g., Claude 3 might allow responses up to a few thousand tokens. Setting `max_tokens` too high isn’t usually an issue except for cost; the model may stop earlier if it finishes the answer.
* **Input Length:** There is a limit of 100,000 messages per request, which is very high. Practically, input is limited by the context token count. If you exceed the model’s context size, the API will error. Plan to chunk extremely large content (e.g. process a website in sections) if needed.
* **Streaming Deltas:** When streaming, accumulate the `content_block_delta` events to reconstruct the answer. Make sure your code can handle event ordering and the final `message_stop` event indicating completion. Best practice is to stream results to the user (for instance, progressively update a Slack message or console output) so they see progress.
* **Stop Sequences:** You can specify `stop_sequences` (array of strings) in the request to instruct Claude to stop generating when those substrings appear. Use this if you want to cut off responses at certain delimiters.
* **System Prompt Usage:** Use the `system` parameter for high-level role or context, but put the actual task or question in the `user` message. Claude treats the system instructions as higher priority guidelines.

By following these practices, you can effectively leverage Claude’s API to analyze and summarize webpage content in the defacement monitor (for example, asking Claude to explain differences between versions or assess if a change is malicious).

**References:** Anthropic API Docs, Message formatting, System prompt usage, Streaming guide.

## Slack Bolt for Python (Async)

Slack Bolt is a high-level framework for building Slack apps in Python. The Web Defacement Monitor uses Slack Bolt (asyncio variant) to integrate with Slack – e.g. providing slash commands to manage monitored sites and sending alerts to channels. This section covers setting up a Slack app, authenticating in code, defining commands/events, posting messages with formatting, and performing permission checks.

### Setting Up a Slack App and Installing Bolt

1. **Create a Slack App:** Go to Slack’s API site and create a new app (choose the workspace where you’ll use it). Add the **Slash Commands** feature if you plan to use commands (e.g., `/monitor`). Define your slash command (name and description) and set its Request URL (this will be an endpoint in your app that Slack calls, typically `/slack/events` or a specific route).
2. **Bot Token and Scopes:** Under **OAuth & Permissions**, assign scopes. For example, `commands` (for slash commands) and `chat:write` (to post messages) are commonly needed. Install the app to your workspace and get the **Bot User OAuth Token** (starts with `xoxb-...`).
3. **Signing Secret:** From your app’s **Basic Information**, grab the Signing Secret. This is used to verify Slack’s requests in your app.
4. **Install Slack Bolt (Python):**

   ```bash
   pip install slack_bolt aiohttp
   ```

   (Bolt’s async mode uses AIOHTTP under the hood, so ensure `aiohttp` is installed.)

### Initializing the Async App (Authentication)

Use the `AsyncApp` class to create your Slack app in Python. Provide the bot token and signing secret:

```python
import os
from slack_bolt.async_app import AsyncApp

app = AsyncApp(
    token=os.getenv("SLACK_BOT_TOKEN"),               # xoxb-... token
    signing_secret=os.getenv("SLACK_SIGNING_SECRET")  # signing secret
)
```

This creates a Bolt app that will handle Slack events asynchronously. The framework automatically verifies incoming requests using the signing secret (ensuring security). By default, `AsyncApp` starts an internal web server (AIOHTTP based) when you call `app.start()`, listening on port 3000 or a port you choose. Ensure your Slack app’s Request URL matches `/slack/events` on your server and that the port is accessible.

**Note:** Alternatively, you can integrate Bolt with other ASGI frameworks (FastAPI, Sanic, etc.) using adapters, but the built-in server is convenient for simple deployments.

### Defining Slash Commands and Event Handlers

Slack Bolt makes it easy to define handlers for various interactions:

* **Slash Commands:** Use `@app.command("/yourcommand")` decorator for an async function.
* **Events:** Use `@app.event("event_name")` for events (like message events).
* **Actions/Shortcuts:** Use `@app.action(...)` or `@app.shortcut(...)` similarly.

**Slash Command Example:** Define a command `/monitor` to add a site to monitor:

```python
@app.command("/monitor")
async def handle_monitor(ack, body, say):
    await ack()  # Acknowledge the command request immediately
    user_id = body.get("user_id")
    text = body.get("text")  # text after the command, e.g., a URL or subcommand
    # (Permission check example)
    if user_id not in AUTHORIZED_USER_IDS:
        await say("Sorry, you are not authorized to use this command.")
        return
    # ...perform the monitoring setup (e.g., schedule a job, etc.)
    await say(f"✅ Monitoring initiated for {text}")
```

In this snippet, we use `ack()` to confirm receipt to Slack (to avoid a timeout), then `say()` to send a response back in the channel (or as an ephemeral message to the user in case of slash commands). The `body` dict contains details like the user ID and text. We included a simple permission check: comparing `user_id` against an allowed list and responding accordingly.

**Event Example:** If we wanted to respond when the bot is mentioned:

```python
@app.event("app_mention")
async def mention_handler(event, say):
    user = event["user"]
    await say(f"Hi <@{user}>, I'm alive and monitoring websites!")
```

This would listen for any mention of the bot and reply in the same channel.

After defining your handlers, start the app:

```python
if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 3000)))
```

This will run the web server to handle incoming Slack requests.

### Posting Messages with Formatting and Attachments

Within command or event handlers, you have multiple ways to send messages:

* **Using `say()` or `respond()`:** These convenience methods are provided by Bolt. In a slash command context, `respond()` sends a response visible only to the command user by default, whereas `say()` posts a message to the channel where the command was used. For event handlers, `say()` posts to the channel of the event.
* **Using `client` object:** You can access the Slack Web API client via `app.client` or the injected `client` argument. For example, `await client.chat_postMessage(channel=..., text=..., blocks=...)` for advanced usage.

Slack messages support *Markdown-like* formatting (mrkdwn). For example, you can include `*bold*` or `` `code` `` or even multi-line triple backtick blocks for code. Ensure that in your API call, `mrkdwn` is enabled (it is by default in most cases).

**Attachments vs Blocks:** Slack’s newer UI uses **Block Kit** (blocks) for rich message layouts (sections, buttons, etc.). Older style *attachments* (with color bars, fields) are still supported. For simplicity:

* To add a quick attachment: include an `attachments=[ {...} ]` parameter in `say()` or `chat_postMessage`. For example:

  ```python
  await say(text="Site Status", attachments=[{
      "color": "#ff0000",
      "title": "Defacement Detected",
      "text": "Example.com homepage content has changed by 45%!"
  }])
  ```

  This would post a message with a colored side bar and the attachment text.
* To use Block Kit: construct a `blocks=[...]` list. For example:

  ```python
  await say(blocks=[
      {"type": "section", "text": {"type": "mrkdwn", "text": "*Defacement Alert:* Example.com changed!"}},
      {"type": "actions", "elements": [
          {"type": "button", "text": {"type": "plain_text", "text": "View Diff"}, "url": diff_url}
      ]}
  ])
  ```

  This uses a section block with bold text and an action button. Blocks allow intricate formatting and interactive components.

**Ephemeral vs Public Replies:** By default, responding to a slash command without explicitly marking it "in\_channel" will only show the message to the user who invoked the command (ephemeral). If you want the response visible to everyone in the channel, you can set the response payload to include `"response_type": "in_channel"`. In Bolt, `say()` in a command handler posts in channel (since it uses bot token to post), whereas `respond()` can be used for ephemeral replies.

### Verifying Users and Permissions

For security, ensure only authorized users can trigger certain actions:

* Use the `body["user_id"]` or `event["user"]` to identify who initiated the action. Compare against a configured list of admins or allowed users. (In our slash command example above, we did this check and returned an error message if unauthorized.)
* You can also verify the channel: e.g., only allow certain commands in specific Slack channels by checking `body["channel_id"]` or event channel.
* Slack Bolt handles verifying that incoming requests genuinely come from Slack (using the signing secret). Keep this feature on (it’s on by default).
* Consider rate limiting or debouncing commands if a user could spam them (Slack might impose its own rate limits too).

### Running the Slack App

If running in a web service, you might prefer not to use `app.start()` (which starts its own web server). Instead, integrate with an ASGI server:

* Bolt provides adapters for frameworks (like Sanic, FastAPI, etc.). For example, using Sanic:

  ```python
  from slack_bolt.adapter.sanic import AsyncSlackRequestHandler
  api = Sanic(__name__)
  handler = AsyncSlackRequestHandler(app)

  @api.post("/slack/events")
  async def slack_events(request):
      return await handler.handle(request)
  ```

  Then run Sanic with `api.run(...)` or via Uvicorn.
* Alternatively, using Socket Mode (if you cannot expose an HTTP endpoint) – Bolt can connect via WebSocket to Slack. This requires enabling Socket Mode in your app and using `AsyncApp(token=..., signing_secret=..., socket_mode=True)`.

For the Web Defacement Monitor, using the built-in AIOHTTP server with `app.start()` on a standard port (and making sure that port is accessible or behind a reverse proxy) is a straightforward approach.

**References:** Slack API docs on slash commands, Slack Bolt (Python) async usage, Bolt slash command handler example, Slack message formatting guide.

## Playwright for Python (Headless Chromium)

The defacement monitor uses Playwright to fetch live web page content in a headless browser environment. Playwright can render JavaScript-heavy sites (unlike simple HTTP fetching), ensuring we get the fully rendered DOM for accurate comparisons. This section covers installing Playwright on Linux/Docker, using headless Chromium, waiting for dynamic content, extracting page data, and managing browser sessions efficiently.

### Installation (Linux/Docker) and Setup

**Install package:** In your Python environment, install Playwright:

```bash
pip install playwright
```

After installation, you need to install browser binaries. Run:

```bash
playwright install
```

This downloads Chromium (and Firefox/WebKit) drivers. In Docker or CI, you can use `playwright install --with-deps` to also install OS dependencies. For example, a Dockerfile snippet:

```Dockerfile
FROM python:3.12-slim
RUN pip install playwright==1.52.0 && \
    playwright install --with-deps
```

This ensures all necessary libraries (like libatk, libnss, fonts, etc.) are present for headless Chromium.

**Headless mode:** By default, Playwright launches browsers in headless mode (no UI). This is ideal for servers. Ensure the container/VM has proper environment for Chrome (Xvfb is not needed for true headless). If issues arise (e.g., sandbox errors), you may try launching with arguments like `--no-sandbox` or use Docker flags like `--ipc=host` and `--init` as recommended.

### Navigating to Pages and Waiting for Dynamic Content

To use Playwright, initialize it and open a page. Example using the async API:

```python
from playwright.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context()
    page = await context.new_page()
    # Navigate to the URL and wait for it to load
    await page.goto("https://example.com", wait_until="networkidle")
    # Now page is fully loaded (no network activity for 500ms)
    html = await page.content()
    print("HTML content length:", len(html))
    await browser.close()
```

In the code above:

* We launch Chromium in headless mode.
* `wait_until="networkidle"` in `page.goto()` tells Playwright to consider navigation done when the network is idle (no new requests for 500ms). This is useful for single-page apps or pages that load additional data asynchronously. (Playwright’s docs note that `networkidle` is sometimes **discouraged** for tests since it might be too lenient, but for scraping it helps ensure we get dynamic content.)
* We then call `page.content()` to get the full HTML markup of the page. This includes content that was added by JavaScript after initial load, and it retains the doctype and full DOM structure.

**Alternative waiting strategies:** Instead of `networkidle`, you can wait for specific elements or events:

* `await page.wait_for_selector("css=selector")` to wait for a particular element to appear.
* `await page.wait_for_load_state("domcontentloaded")` or `"load"` for simpler pages.
* In many cases, simply doing `page.goto()` without specifying `wait_until` will wait for the `load` event (all resources like images loaded), which may be sufficient.

### Extracting Content, Text, and Links

Once the page is loaded, you can extract the data needed:

* **Full HTML:** `page.content()` as shown, returns a string with the HTML source of the current DOM. You could save this or compute a hash for defacement detection.
* **Text content:** If you want just visible text, you can use `page.text_content("body")` or the newer locator API: `await page.locator("body").inner_text()`. This gives the concatenated text of the page’s body (without HTML tags).
* **Specific elements:** Use Playwright’s selectors or locators:

  * Example: `title = await page.title()` to get `<title>` text.
  * Example: `links = await page.locator("a").all()` to get all anchor elements, then for each do `await link.get_attribute("href")` to get URLs.
  * Example: `element = await page.query_selector("h1")` then `await element.inner_text()` to get an H1 text.
* **Screenshots:** (Optional) `await page.screenshot(path="page.png")` if you want a snapshot of the page. This can be useful for logging defacement evidence.

**Handling multiple frames:** If the page has iframes, be aware `page.content()` will include the outer HTML but not the inner contents of iframes by default. You’d need to switch to those frames via `frame = page.frame(name="frameName")` and then extract content from `frame`.

**Network data:** Playwright can also intercept network requests if needed, but for defacement monitoring typically the rendered content is enough. If you needed to ensure no unexpected redirects or to gather all resources, you could use `page.on("response", ...)` events.

### Managing Browser Sessions Efficiently

**Reusing browser contexts:** Launching a browser is an expensive operation (it starts a Chromium instance). For performance, you can launch the browser once and open multiple pages (or reuse one page for sequential navigations). For example, if monitoring multiple sites, it might be wise to do:

```python
browser = await playwright.chromium.launch(headless=True)
context = await browser.new_context()
page = await context.new_page()
for url in urls_to_check:
    await page.goto(url, wait_until="networkidle")
    # ... extract content ...
```

This keeps the browser alive. However, be mindful of state:

* If you want isolated sessions (no cookies/cache shared), use separate contexts for each site or clear context between navigations.
* Closing the context or browser frees resources. On a schedule (like APScheduler job), it might be fine to open fresh each time, but that adds overhead. A middle ground is to keep one browser running and perhaps a pool of contexts.

**Memory and Timeouts:** Headless browsers can consume memory. If scanning many sites, ensure to close pages when done (`await page.close()` or reuse one page). Also set timeouts as needed:

* The default navigation timeout might be 30s. You can adjust: `page.set_default_navigation_timeout(15000)` for 15s if you want faster failure.
* If a site is very slow or hangs, consider using `page.goto(..., timeout=ms)` or wrapping in your own timeout logic.

**Error handling:** Wrap navigation in try/except to catch `TimeoutError` or other errors. If a page fails to load or is not reachable, you might mark that site as down and not trigger a false defacement alert.

**Resource Blocking:** Optionally, to speed up load and focus on textual content, you can block certain resources (like images, ads). Playwright’s route interception can abort requests for images or other resource types. Example:

```python
await context.route("**/*.{png,jpg,jpeg,gif}", lambda route: route.abort())
```

This aborts image requests. This can make page load faster and still get textual content (unless the site depends on images for content).

**Headful vs Headless:** For debugging, you can launch with `headless=False` to see the browser window (requires a display or X11 forwarding). Not needed in production.

By using Playwright, the monitor gets a **fully rendered DOM** and thus can detect defacement even on sites that build content dynamically via JavaScript. Always test with a variety of site types (static, SPAs, login pages if needed) to ensure your waiting strategy captures the content you need.

**References:** Playwright Python documentation on `page.goto` and load states, page content retrieval, navigation events.

## Qdrant (Vector Database for Embeddings)

Qdrant is a vector database that stores high-dimensional vectors (like text embeddings) and allows efficient similarity search. In the Web Defacement Monitor, Qdrant can be used to store embeddings of website content (or chunks of content) for anomaly detection – for example, comparing the latest content vector to previous ones or searching for similar known defacement patterns. This section covers using Qdrant’s Python client to create collections, insert vectors with metadata, and query by vector similarity.

### Setting Up a Collection in Qdrant

First, install the Qdrant client:

```bash
pip install qdrant-client
```

You also need a running Qdrant service (local or Qdrant Cloud). The client can connect via REST or gRPC. For local testing, you can even use an in-memory mode.

**Initializing the client:**

```python
from qdrant_client import QdrantClient
client = QdrantClient(url="http://localhost:6333")  # or QdrantClient(":memory:")
```

Replace the URL with your Qdrant instance. (If using Qdrant Cloud, you’ll also have an API key.)

**Creating a collection:** Decide on a collection name, vector size (dimension of your embeddings, e.g., 1536 for OpenAI embeddings), and similarity metric (e.g., cosine or dot product). Example:

```python
from qdrant_client.http.models import Distance, VectorParams

collection_name = "site_content_vectors"
if not client.collection_exists(collection_name):
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
    )
```

This will create a new collection if it doesn’t exist, expecting 1536-dimensional vectors and using cosine similarity. The distance metric can be `Distance.COSINE`, `Distance.DOT` (dot product), or `Distance.EUCLID` depending on how you want similarity computed. Cosine is common for normalized embeddings.

Qdrant will assign this collection a name and allow CRUD operations on points (vectors with IDs and payloads) within it.

### Inserting Embeddings with Metadata

To store data, you typically have:

* A vector (list of floats, the embedding of a site’s content or a chunk).
* An ID for the vector (unique per vector).
* Optional **payload**: a JSON-like object of metadata (e.g., site URL or ID, chunk identifier, timestamp, hash).

You can insert (upsert) points in Qdrant as follows:

```python
from qdrant_client.http.models import PointStruct

points = [
    PointStruct(id=1, vector=embed1, payload={"site_id": 101, "chunk_hash": "abc123", "url": "http://example.com"}),
    PointStruct(id=2, vector=embed2, payload={"site_id": 101, "chunk_hash": "def456", "url": "http://example.com"})
]
result = client.upsert(collection_name=collection_name, points=points)
```

This will insert or update two vectors with specified IDs. If an ID already exists, it will update that point. The payload stores metadata: here we include a `site_id` (internal identifier for the site), a `chunk_hash` (maybe a hash of the chunk content for change detection), and the URL. You can customize payload fields as needed (e.g., a timestamp of when the scan was done).

Alternatively, Qdrant’s client has a convenient `add` method if you use its embedding module, but in our case we likely compute embeddings via an external model (like OpenAI or SBERT), so using `upsert`/`PointStruct` is straightforward.

**Choosing IDs:** You need unique IDs for points. You could use a composite like site\_id + chunk index, or a hash. For example, if each site has multiple content chunks, an ID could be `f"{site_id}_{chunk_hash}"` or just let Qdrant assign random UUIDs if you call `client.upload_collection` or similar. However, specifying IDs can help avoid duplicates on re-insertion.

### Similarity Search Queries

Once vectors are stored, Qdrant can perform similarity search to find nearest neighbors or to detect if a new embedding is an outlier compared to historical ones:

**Basic vector search:**

```python
query_vector = new_embed  # e.g., embedding of latest content
results = client.search(
    collection_name=collection_name,
    query_vector=new_embed,
    limit=5
)
for point in results:
    print(point.id, point.score, point.payload.get("site_id"))
```

This finds the 5 closest vectors to `new_embed` in the entire collection. Each `point` in results has a `.score` (the similarity score – higher usually means more similar for dot/cosine) and you can access the payload for context.

**Filtered search:** Often, you want to restrict search to the same site or a subset. For example, to find similar vectors *for the same site only*, you can use a filter on the payload:

```python
from qdrant_client.http.models import Filter, FieldCondition, MatchValue

results = client.search(
    collection_name=collection_name,
    query_vector=new_embed,
    query_filter=Filter(must=[
        FieldCondition(key="site_id", match=MatchValue(value=101))
    ]),
    limit=5
)
```

This will only search among points where `site_id == 101`. You can combine multiple conditions in the filter (e.g., also same chunk type or date range, etc., using `must`/`should` clauses).

**Interpreting results:** If the top result’s score is significantly lower than perfect (depending on your metric), it might indicate the new content is very different from past content (possible defacement). For cosine, scores range -1 to 1 (1 is identical). For dot product with normalized vectors, it’s similar (0 to 1 if normalized). You may set a threshold or alert if similarity drops below a certain level compared to the previous scan.

**Metadata usage:** We stored `chunk_hash` in payload – you might use this to quickly check if an exact content chunk was seen before. For instance, if you split page content into chunks and one chunk’s hash is entirely new, that’s a change. Qdrant can be queried by metadata alone if needed (though it’s more for vector queries).

**Upsert vs Append:** Using `upsert` is convenient in that it will add or update. If you want to keep an **history** of embeddings (not overwrite old ones), ensure you use unique IDs each time (like include a timestamp or version in the ID). Otherwise, you might choose to not use `upsert` but rather use `client.retrieve` to check and then decide to insert with new ID.

**Deleting:** Qdrant allows deleting by IDs or filtering. If you remove a site, you might delete by filter `site_id = ...`.

**Collection management:** Collections can be updated (e.g., change replication factor) but dimension and distance metric are fixed at creation. If you need to change the vector dimension (say you switch embedding model), you’d make a new collection.

**Performance:** Qdrant uses indexes (HNSW by default) to make searches fast even for large collections. You might configure the HNSW parameters if needed for trade-offs between speed and accuracy, but defaults are fine. Also consider enabling `quantization` if you have huge numbers of vectors and want to save memory.

Qdrant’s vector search is very useful to detect *semantic* changes – for instance, if the site content is changed to something entirely different (even if some words overlap), the embedding will shift and cosine similarity can catch that beyond simple hash comparisons.

**References:** Qdrant Python client quickstart (creating collection), inserting points, basic search, filtered search.

## APScheduler (Job Scheduling)

The monitor likely needs to periodically re-scan websites (e.g., every 5 minutes or every hour) and possibly schedule one-off or dynamic jobs (like a new site gets added, schedule its checks). **APScheduler** is a Python library that provides cron-like scheduling within applications. It can run background jobs on intervals, at specific times (cron), or once.

### Choosing a Scheduler and Getting Started

APScheduler provides different scheduler implementations:

* **BackgroundScheduler:** Runs jobs in a background thread, suitable for apps (doesn’t block the main thread).
* **BlockingScheduler:** Runs jobs in the main thread (blocks it) – useful for standalone scripts.
* **AsyncIOScheduler:** If using an asyncio event loop (could be relevant since Slack Bolt uses asyncio), you might use this so jobs run in the loop.

For most cases in a web app context, **BackgroundScheduler** is a good choice. It will spawn a thread for scheduling and use a thread pool for jobs by default.

**Install APScheduler:**

```bash
pip install apscheduler
```

**Initialize the scheduler:**

```python
from apscheduler.schedulers.background import BackgroundScheduler
scheduler = BackgroundScheduler()
scheduler.start()
```

This starts the scheduler with an in-memory job store and a thread pool executor (default 10 threads). You can configure job stores (e.g., use a database to persist jobs) and executors (thread or process pool) if needed, but for a simple use the defaults are fine. Ensure to call `start()` after adding jobs (or you can add jobs before start; they’ll run once started).

### Scheduling Jobs (Interval and Cron)

APScheduler supports different trigger types:

* **Interval:** e.g., every 5 minutes.
* **Cron:** like UNIX cron expressions or fields (specific days of week, times, etc.).
* **Date:** one-time job at a specific datetime.

For a defacement monitor, you might use interval (every X minutes) or cron (e.g., at certain times each day).

**Add an interval job:**

```python
def scan_site(site_id):
    # function to perform scanning (could call Playwright, etc.)
    ...

# Schedule scan_site to run every 10 minutes
scheduler.add_job(scan_site, 'interval', minutes=10, args=[101], id='scan_101')
```

This will call `scan_site(101)` every 10 minutes. We gave it an `id` so we can modify or remove it later. If the function to execute is not pickleable (for certain APScheduler job stores), define it at top-level. Using `args` or `kwargs` lets you pass parameters.

**Add a cron job:**

```python
scheduler.add_job(scan_site, 'cron', hour=0, minute=0, args=[101], id='scan_101_daily')
```

This would run `scan_site(101)` every day at midnight. Cron trigger can accept fields like `day_of_week='mon-fri'`, or lists like `hour='9,12,15'`, and even ranges or `*/5` notation (every 5 units). For example, `minute='*/5'` means every 5 minutes.

Under the hood, `'cron'` trigger is a flexible way to set schedules (much like crontab). APScheduler also allows specifying a `start_date` or `end_date` for jobs if needed.

If your app is long-running, the scheduler will keep triggering jobs on schedule. You might integrate it such that each site added via Slack command creates a job:

```python
scheduler.add_job(scan_site, 'interval', minutes=5, args=[new_site_id], id=f"scan_{new_site_id}", replace_existing=True)
```

Using `replace_existing=True` ensures that if a job with that ID exists (e.g., you schedule again), it will update instead of duplicating.

### Removing or Modifying Jobs Dynamically

You can remove jobs by ID:

```python
scheduler.remove_job('scan_101')  # cancels the job with that ID
```

After removal, it won’t run anymore. Alternatively, if you kept the `Job` object from `add_job`, you can call `job.remove()`.

If using persistent job stores (like database), note that APScheduler will reload jobs on restart. If you schedule jobs at runtime and restart the app often, consider using an explicit ID with `replace_existing` to avoid duplicate scheduling on each start.

**Modifying jobs:** There is a `reschedule_job()` method if you just want to change the timing of an existing job. For example:

```python
scheduler.reschedule_job('scan_101', trigger='cron', minute='*/5')
```

would change job `scan_101` to run every 5 minutes. You can also pause jobs (`scheduler.pause_job(id)`) and resume them (`resume_job`).

### APScheduler in Async Environment

Since our Slack app is async, note that BackgroundScheduler by default runs in separate thread(s). It should still work fine alongside an asyncio app, but APScheduler also offers `AsyncIOScheduler` which uses the asyncio loop for job execution. If your scan function itself is an async function, you have a couple options:

* Run it in the loop by scheduling via AsyncIOScheduler (then the function can be `async def`).
* Or have the job function call `asyncio.run()` or schedule the coroutine in the loop manually.

For simplicity, you might keep scan jobs synchronous (or fire-and-forget async tasks). Alternatively, use `AsyncIOScheduler()`:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
scheduler = AsyncIOScheduler()
scheduler.start()
```

Then schedule jobs similarly. This will ensure the coroutine jobs execute in the main asyncio loop (no separate threads). Just be careful that if a job runs long, it may block other async tasks unless awaited properly.

### Best Practices

* **Thread safety:** If your job function touches shared data (like a list of sites), use thread-safe structures or locks, or use AsyncIOScheduler to avoid multi-threading issues.
* **Error handling:** APScheduler by default will catch exceptions in jobs and can log them. You can set `job_defaults={'misfire_grace_time': 30}` when creating scheduler to allow a job to run even if it missed its time by up to 30 seconds (e.g., if the app was asleep).
* **Shutting down:** On application exit, call `scheduler.shutdown()` to gracefully stop.

By using APScheduler, the monitor can dynamically add jobs when a user registers a site (via slash command) and remove them when unregistered, providing flexible scheduling much like cron but controlled via the Slack interface.

**References:** APScheduler user guide on adding/removing jobs, example of removing job by ID.

## SQLite Database via SQLAlchemy (Storing Scans & Hashes)

To keep track of scan results, the monitor can use a lightweight SQLite database (file or in-memory). SQLAlchemy provides an ORM or SQL toolkit to interact with SQLite in a high-level way. We’ll discuss designing a schema for scans and content hashes, and how to efficiently read/write data using SQLAlchemy.

### Database Schema Design for Scans

For defacement monitoring, you likely need to store:

* A list of sites being monitored (with details like URL, maybe frequency, etc.).
* The last known hash of each site’s content (to detect changes).
* Possibly a history of changes or a log of scans.

A simple schema could be:

```python
Base = declarative_base()

class Site(Base):
    __tablename__ = 'sites'
    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True)
    last_hash = Column(String)
    last_scan = Column(DateTime)
    # perhaps other fields like created_at, etc.
```

This `Site` table stores each monitored site, and the last known content hash and scan time. Each time we scan, we compare the new hash with `last_hash`:

* If it’s different, we might raise an alert and update `last_hash`.
* Always update `last_scan` with the current timestamp.

If you want to maintain a history of scans (to see past hashes or when changes occurred), you could have a separate table:

```python
class ScanEvent(Base):
    __tablename__ = 'scan_events'
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey('sites.id'))
    scan_time = Column(DateTime)
    content_hash = Column(String)
    defacement_detected = Column(Boolean)
```

This table could log every scan event, marking whether a defacement (change) was detected. The `Site` table would then only track the current state.

For initial implementation, a single `Site` table might suffice, updating the hash in place.

### Setting Up the Database with SQLAlchemy

**Engine and connection:** Use SQLAlchemy’s engine to connect to SQLite. For a file database:

```python
from sqlalchemy import create_engine
engine = create_engine("sqlite:///monitor.db")
```

This will create a SQLite file `monitor.db` in the current directory (or connect to it if exists).

**Define models:** As shown above, use the ORM’s Declarative system:

```python
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
Base = declarative_base()

class Site(Base):
    __tablename__ = 'sites'
    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True)
    last_hash = Column(String)
    last_scan = Column(DateTime)
```

You can then create the tables in the database:

```python
Base.metadata.create_all(engine)  # Create tables according to the models
```

This will emit the necessary `CREATE TABLE` statements for all defined models.

If using the `ScanEvent` table with a ForeignKey, ensure to define the relationship (or at least the foreign key) and call `create_all` as well.

**Sessions:** To interact with the DB, create a session:

```python
from sqlalchemy.orm import sessionmaker
SessionLocal = sessionmaker(bind=engine)

# Example usage:
session = SessionLocal()
# ... perform DB operations ...
session.close()
```

Using a context manager (`with SessionLocal() as session:`) is also a good pattern to auto-close.

### Reading and Writing Data Efficiently

With the schema in place:

* **Adding a new site:**

  ```python
  def add_site(url):
      with SessionLocal() as session:
          site = Site(url=url, last_hash="", last_scan=None)
          session.add(site)
          session.commit()
          return site.id
  ```

  This inserts a new row into `sites`. If using Slack command to add, you’d call this, then perhaps schedule a job.

* **Updating hash after scan:**

  ```python
  def update_site_hash(site_id, new_hash, defacement):
      with SessionLocal() as session:
          site = session.query(Site).get(site_id)
          if site:
              site.last_hash = new_hash
              site.last_scan = datetime.utcnow()
              session.commit()
  ```

  Here we retrieve the Site by primary key, update fields, and commit. Using `query.get` (or in SQLAlchemy 2.x, `session.get(Site, site_id)`) is efficient for primary key lookup.

* **Checking for changes:** Before updating, you likely compare `new_hash != site.last_hash` to decide if defacement occurred. That logic would be in your scanning routine rather than the DB code.

* **Logging events:** If using `ScanEvent`, you’d create a ScanEvent object and add it:

  ```python
  event = ScanEvent(site_id=site.id, scan_time=datetime.utcnow(),
                    content_hash=new_hash, defacement_detected=(new_hash != site.last_hash))
  session.add(event)
  ```

  This way every scan is recorded. Just be mindful that the events table can grow; you might periodically prune old entries or use SQLite’s archival strategies.

**Efficient Bulk Operations:** If scanning many sites at once, SQLAlchemy allows bulk inserts/updates:

* `session.bulk_save_objects([...])` or `session.bulk_insert_mappings()` to insert multiple rows without overhead of instances.
* However, for a moderate number of sites, simple loop with session adds is fine.

**Indexes:** Ensure you have indexes on fields you query frequently. In our `Site` table, `url` is unique – it gets an implicit index due to `unique=True`. If you often query by `last_hash` or other fields, consider adding `index=True` in Column definition. For relationships, foreign key fields are indexed by default in many databases (SQLite will index the PKs but not necessarily FKs, so add index on `ScanEvent.site_id` if that table grows).

**Concurrency:** If the Slack commands and the scheduler run in the same process, be careful with the session usage. Multiple threads (like APScheduler background jobs) should each use their own session. The sessionmaker as shown can be called in each thread. SQLite has write serialization (only one write at a time), so committing from two threads at once can lock – ensure quick transactions or consider using a threading lock around DB writes if needed. Alternatively, use APScheduler with a `processpool` executor or external queue to handle DB writes in one place.

**WAL mode:** For higher write concurrency in SQLite, you can enable WAL journal mode by executing `PRAGMA journal_mode=WAL;` on connection. SQLAlchemy can do this via event listeners or you can set in SQLite URI (`sqlite:///monitor.db?check_same_thread=False` and then a PRAGMA).

**Example Query:** To retrieve all sites to scan:

```python
with SessionLocal() as session:
    sites = session.query(Site).all()
    for site in sites:
        print(site.id, site.url, site.last_hash)
```

This loads all sites. If the list is large, you could stream (iterate a query with `yield_per`), but for tens or hundreds of sites it’s fine.

### Example Combined Usage

Putting it together, a scan job might:

```python
with SessionLocal() as session:
    site = session.query(Site).filter_by(id=site_id).one_or_none()
    if not site:
        return
    old_hash = site.last_hash
    content = fetch_site_content(site.url)  # use Playwright in this function
    new_hash = hash_content(content)
    if new_hash != old_hash:
        alert_defacement(site.url, old_hash, new_hash)  # e.g., send Slack alert
        site.last_hash = new_hash
    site.last_scan = datetime.utcnow()
    session.commit()
    # Optionally log event
    session.add(ScanEvent(site_id=site.id, scan_time=site.last_scan,
                          content_hash=new_hash, defacement_detected=(new_hash != old_hash)))
    session.commit()
```

This pseudo-code checks for changes and updates accordingly. Note we commit twice: once for the site update and once for adding the event – we could do it in one transaction as well (add the event before commit).

SQLAlchemy will handle translating these operations to SQL under the hood.

For small scale, SQLite’s performance is fine. If your usage grows (hundreds of sites, very frequent scans), you might consider a more robust DB or use Qdrant fully for storing content fingerprints. But SQLite gives an easy starting point and a persistent local record of what happened.

**References:** SQLAlchemy declarative model example, engine creation for SQLite, creating tables.
