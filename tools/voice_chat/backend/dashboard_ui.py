"""Dashboard HTML template for Raj unified inbox."""


def render_dashboard_html() -> str:
    return """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Raj Unified Inbox</title>
  <style>
    :root {
      --bg: #eef3e9;
      --panel: #fcfff8;
      --ink: #1f2b1d;
      --muted: #60705f;
      --line: #d9e5d2;
      --accent: #2f7f58;
      --warn: #b4551f;
      --high: #b52a2a;
      --chip: #edf5ea;
      --shadow: 0 14px 32px rgba(30, 45, 26, 0.12);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      font-family: \"IBM Plex Sans\", \"Segoe UI\", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at 10% 0%, rgba(47, 127, 88, 0.14), transparent 35%),
        radial-gradient(circle at 100% 100%, rgba(223, 174, 78, 0.18), transparent 35%),
        var(--bg);
      min-height: 100vh;
    }

    .shell {
      max-width: 1500px;
      margin: 0 auto;
      padding: 24px;
    }

    .header {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 18px;
    }

    .title {
      margin: 0;
      font-size: clamp(1.4rem, 2.1vw, 2rem);
      letter-spacing: -0.02em;
      font-weight: 700;
    }

    .subtitle {
      margin: 4px 0 0;
      color: var(--muted);
      font-size: 0.95rem;
    }

    .actions {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .refresh {
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--ink);
      border-radius: 999px;
      padding: 8px 14px;
      font-weight: 600;
      cursor: pointer;
    }

    .refresh:hover { border-color: var(--accent); }

    .tick {
      color: var(--muted);
      font-size: 0.9rem;
    }

    .alerts {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }

    .alert-card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px;
      box-shadow: var(--shadow);
    }

    .alert-label {
      font-size: 0.8rem;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 8px;
    }

    .alert-value {
      font-size: 1.8rem;
      font-weight: 700;
      margin: 0;
    }

    .alert-note {
      color: var(--muted);
      margin-top: 4px;
      font-size: 0.9rem;
    }

    .alert-urgent .alert-value { color: var(--high); }
    .alert-priority .alert-value { color: var(--warn); }
    .alert-special .alert-value { color: var(--accent); }

    .banner {
      border: 1px dashed var(--line);
      border-radius: 14px;
      padding: 10px 12px;
      background: rgba(252, 255, 248, 0.8);
      margin-bottom: 18px;
      color: var(--muted);
      font-size: 0.94rem;
    }

    .columns {
      display: grid;
      grid-template-columns: repeat(4, minmax(220px, 1fr));
      gap: 12px;
    }

    .column {
      min-height: 300px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 16px;
      overflow: hidden;
      box-shadow: var(--shadow);
      display: flex;
      flex-direction: column;
    }

    .column-head {
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: rgba(237, 245, 234, 0.8);
      font-weight: 700;
      font-size: 0.93rem;
    }

    .count-chip {
      background: var(--chip);
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 0.8rem;
      color: var(--muted);
    }

    .list {
      padding: 10px;
      overflow: auto;
      display: flex;
      flex-direction: column;
      gap: 10px;
      max-height: 68vh;
    }

    .item {
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #fff;
      padding: 10px;
    }

    .item.high {
      border-color: rgba(181, 42, 42, 0.45);
      box-shadow: inset 3px 0 0 rgba(181, 42, 42, 0.8);
    }

    .item.medium {
      border-color: rgba(180, 85, 31, 0.4);
      box-shadow: inset 3px 0 0 rgba(180, 85, 31, 0.7);
    }

    .item.unread {
      background: #fdf8ef;
    }

    .top {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 8px;
      margin-bottom: 6px;
    }

    .name {
      margin: 0;
      font-weight: 700;
      font-size: 0.95rem;
      color: var(--ink);
    }

    .time {
      color: var(--muted);
      font-size: 0.77rem;
      white-space: nowrap;
    }

    .preview {
      margin: 0 0 8px;
      color: #2f3d2d;
      line-height: 1.35;
      font-size: 0.9rem;
    }

    .tags {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }

    .tag {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 0.73rem;
      text-transform: uppercase;
      color: var(--muted);
      background: var(--chip);
    }

    .tag.unread { color: var(--warn); border-color: rgba(180, 85, 31, 0.38); }
    .tag.special { color: var(--accent); border-color: rgba(47, 127, 88, 0.35); }
    .tag.high { color: var(--high); border-color: rgba(181, 42, 42, 0.42); }

    .empty {
      border: 1px dashed var(--line);
      border-radius: 10px;
      color: var(--muted);
      font-size: 0.84rem;
      text-align: center;
      padding: 24px 10px;
      background: rgba(255, 255, 255, 0.55);
    }

    @media (max-width: 1200px) {
      .columns { grid-template-columns: repeat(2, minmax(220px, 1fr)); }
      .list { max-height: 56vh; }
    }

    @media (max-width: 760px) {
      .shell { padding: 14px; }
      .columns { grid-template-columns: 1fr; }
      .list { max-height: 48vh; }
    }
  </style>
</head>
<body>
  <div class=\"shell\">
    <header class=\"header\">
      <div>
        <h1 class=\"title\">Raj Unified Inbox</h1>
        <p class=\"subtitle\">One screen for email, website, Instagram, and TikTok.</p>
      </div>
      <div class=\"actions\">
        <button id=\"refreshBtn\" class=\"refresh\">Refresh</button>
        <span id=\"lastUpdated\" class=\"tick\">Waiting for data...</span>
      </div>
    </header>

    <section class=\"alerts\">
      <article class=\"alert-card alert-urgent\">
        <div class=\"alert-label\">Unread</div>
        <p id=\"unreadValue\" class=\"alert-value\">0</p>
        <div class=\"alert-note\">Messages waiting for response</div>
      </article>
      <article class=\"alert-card alert-priority\">
        <div class=\"alert-label\">Priority</div>
        <p id=\"priorityValue\" class=\"alert-value\">0</p>
        <div class=\"alert-note\">Purchase/complaint/urgent threads</div>
      </article>
      <article class=\"alert-card alert-special\">
        <div class=\"alert-label\">Special Requests</div>
        <p id=\"specialValue\" class=\"alert-value\">0</p>
        <div class=\"alert-note\">Custom design and custom asks</div>
      </article>
    </section>

    <div id=\"alertsBanner\" class=\"banner\">No active alerts right now.</div>

    <section class=\"columns\">
      <article class=\"column\">
        <div class=\"column-head\">Email <span id=\"countEmail\" class=\"count-chip\">0</span></div>
        <div id=\"emailList\" class=\"list\"></div>
      </article>
      <article class=\"column\">
        <div class=\"column-head\">Website <span id=\"countWebsite\" class=\"count-chip\">0</span></div>
        <div id=\"websiteList\" class=\"list\"></div>
      </article>
      <article class=\"column\">
        <div class=\"column-head\">Instagram <span id=\"countInstagram\" class=\"count-chip\">0</span></div>
        <div id=\"instagramList\" class=\"list\"></div>
      </article>
      <article class=\"column\">
        <div class=\"column-head\">TikTok <span id=\"countTiktok\" class=\"count-chip\">0</span></div>
        <div id=\"tiktokList\" class=\"list\"></div>
      </article>
    </section>
  </div>

  <script>
    const lastCounts = { unread: 0, priority: 0, special: 0 };

    function safeTime(iso) {
      if (!iso) return \"\";
      const dt = new Date(iso);
      if (Number.isNaN(dt.getTime())) return \"\";
      return dt.toLocaleString();
    }

    function itemHtml(item) {
      const classes = [\"item\", item.priority || \"low\"];
      if (item.unread) classes.push(\"unread\");

      const tags = [];
      if (item.unread) tags.push('<span class=\"tag unread\">Unread</span>');
      if (item.special_request) tags.push('<span class=\"tag special\">Special request</span>');
      if (item.priority === \"high\") tags.push('<span class=\"tag high\">High priority</span>');
      if (item.intent) tags.push(`<span class=\"tag\">${item.intent}</span>`);
      if (item.response_by) tags.push(`<span class=\"tag\">${item.response_by}</span>`);

      return `
        <article class=\"${classes.join(' ')}\">
          <div class=\"top\">
            <h3 class=\"name\">${item.customer_name || 'Unknown'}</h3>
            <span class=\"time\">${safeTime(item.timestamp)}</span>
          </div>
          <p class=\"preview\">${(item.preview || '').replace(/</g, '&lt;')}</p>
          <div class=\"tags\">${tags.join('')}</div>
        </article>
      `;
    }

    function renderChannel(listId, countId, messages, emptyText) {
      const host = document.getElementById(listId);
      const badge = document.getElementById(countId);
      badge.textContent = String(messages.length);

      if (!messages.length) {
        host.innerHTML = `<div class=\"empty\">${emptyText}</div>`;
        return;
      }

      host.innerHTML = messages.map(itemHtml).join('');
    }

    async function loadDashboard() {
      try {
        const response = await fetch('/dashboard/unified?limit=220');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        const notif = data.notifications || {};
        const channels = data.channels || {};

        document.getElementById('unreadValue').textContent = String(notif.unread || 0);
        document.getElementById('priorityValue').textContent = String(notif.priority || 0);
        document.getElementById('specialValue').textContent = String(notif.special_requests || 0);

        const alertList = (notif.top_alerts || []).join(' | ');
        document.getElementById('alertsBanner').textContent = alertList || 'No active alerts right now.';

        renderChannel('emailList', 'countEmail', channels.email || [], 'No email messages yet.');
        renderChannel('websiteList', 'countWebsite', channels.website || [], 'No website messages yet.');
        renderChannel('instagramList', 'countInstagram', channels.instagram || [], 'No Instagram messages yet.');
        renderChannel('tiktokList', 'countTiktok', channels.tiktok || [], 'No TikTok messages yet.');

        document.getElementById('lastUpdated').textContent = `Updated ${safeTime(data.generated_at)}`;

        // Lightweight notification pulse when counts increase after refresh.
        if (
          (notif.unread || 0) > lastCounts.unread ||
          (notif.priority || 0) > lastCounts.priority ||
          (notif.special_requests || 0) > lastCounts.special
        ) {
          document.title = 'Raj Unified Inbox (New)';
        } else {
          document.title = 'Raj Unified Inbox';
        }

        lastCounts.unread = notif.unread || 0;
        lastCounts.priority = notif.priority || 0;
        lastCounts.special = notif.special_requests || 0;
      } catch (error) {
        document.getElementById('alertsBanner').textContent = `Could not load dashboard data: ${error.message}`;
      }
    }

    document.getElementById('refreshBtn').addEventListener('click', loadDashboard);
    loadDashboard();
    setInterval(loadDashboard, 30000);
  </script>
</body>
</html>
"""