"""
Post-processes a Locust HTML report to inject a non-technical summary section at the top.
Reads stats from the embedded window.templateArgs JSON — no --csv flag needed.

Usage:
    python3 shared/performance/inject_summary.py --html reports/performance/locust_report.html
    # writes to locust_report_summary.html — original is never touched
"""

import argparse
import json
import re
import sys
from pathlib import Path


KEY_APIS = {
    "GET /datasetSync [DAILY_ROLLUP_BY_MENUS] ws-push": "Rollup Sync (App Push)",
    "GET /datasetSync [SCANS] ws-push":                 "Scan Log Sync (App Push)",
    "POST /scans":                                      "Scan Insertion",
}


def _status(failure_pct: float) -> str:
    if failure_pct == 0:
        return '<span class="ok">&#10003; No failures</span>'
    if failure_pct < 5:
        return f'<span class="warn">&#9888; {failure_pct:.1f}% failures</span>'
    return f'<span class="fail">&#10007; {failure_pct:.1f}% failures</span>'


def _ms(val) -> str:
    try:
        return f"{int(float(val))}ms"
    except (ValueError, TypeError):
        return "—"


def _extract_template_args(html: str) -> dict:
    m = re.search(r'window\.templateArgs\s*=\s*(\{.+)', html, re.DOTALL)
    if not m:
        raise ValueError("window.templateArgs not found in HTML")
    raw = m.group(1)
    depth = end = 0
    for i, ch in enumerate(raw):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    return json.loads(raw[:end])


def build_summary(data: dict) -> str:
    stats_by_name = {s["name"]: s for s in data.get("requests_statistics", [])}

    total_requests = sum(s["num_requests"] for s in stats_by_name.values())
    total_failures = sum(s["num_failures"] for s in stats_by_name.values())
    overall_fpct   = (total_failures / total_requests * 100) if total_requests else 0

    duration  = data.get("duration", "")
    host      = data.get("host", "")
    start     = data.get("start_time", "")[:19].replace("T", " ")
    end       = data.get("end_time", "")[:19].replace("T", " ")

    api_rows_html = ""
    for api_name, label in KEY_APIS.items():
        s = stats_by_name.get(api_name)
        if not s:
            continue
        req  = s["num_requests"]
        fail = s["num_failures"]
        fpct = (fail / req * 100) if req else 0
        p50  = _ms(s.get("median_response_time"))
        p99  = _ms(s.get("response_time_percentile_0.99"))
        worst = _ms(s.get("max_response_time"))

        api_rows_html += f"""
        <tr>
            <td class="label">{label}</td>
            <td>{req:,}</td>
            <td>{fail:,}</td>
            <td>{p50}</td>
            <td>{p99}</td>
            <td>{worst}</td>
            <td>{_status(fpct)}</td>
        </tr>"""

    return f"""
<style>
  #perf-summary {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #fff;
    border: 2px solid #e0e0e0;
    border-radius: 10px;
    padding: 28px 36px;
    margin: 28px 28px 0;
    box-shadow: 0 2px 12px rgba(0,0,0,.07);
  }}
  #perf-summary h2 {{
    margin: 0 0 4px;
    font-size: 20px;
    font-weight: 700;
    color: #111;
  }}
  #perf-summary .meta {{
    color: #777;
    font-size: 13px;
    margin-bottom: 24px;
  }}
  #perf-summary .overview {{
    display: flex;
    gap: 20px;
    margin-bottom: 28px;
    flex-wrap: wrap;
  }}
  #perf-summary .stat {{
    background: #f5f6f8;
    border-radius: 8px;
    padding: 14px 22px;
    min-width: 130px;
    flex: 0 0 auto;
  }}
  #perf-summary .stat .val {{
    font-size: 26px;
    font-weight: 700;
    color: #111;
    line-height: 1.1;
  }}
  #perf-summary .stat .key {{
    font-size: 12px;
    color: #999;
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: .04em;
  }}
  #perf-summary table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
  }}
  #perf-summary th {{
    text-align: left;
    padding: 9px 14px;
    background: #f0f1f4;
    color: #555;
    font-weight: 600;
    border-bottom: 2px solid #ddd;
    white-space: nowrap;
  }}
  #perf-summary td {{
    padding: 11px 14px;
    border-bottom: 1px solid #eee;
    color: #333;
    white-space: nowrap;
  }}
  #perf-summary td.label {{ font-weight: 600; color: #111; white-space: normal; }}
  #perf-summary .ok   {{ color: #2e7d32; font-weight: 700; }}
  #perf-summary .warn {{ color: #e65100; font-weight: 700; }}
  #perf-summary .fail {{ color: #c62828; font-weight: 700; }}
  #perf-summary .divider {{
    border: none;
    border-top: 2px solid #e8e8e8;
    margin: 0 0 18px;
  }}
  #perf-summary .two-col {{
    display: flex;
    gap: 32px;
    margin-bottom: 28px;
    flex-wrap: wrap;
  }}
  #perf-summary .two-col > div {{
    flex: 1 1 300px;
  }}
  #perf-summary h3 {{
    font-size: 13px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .06em;
    color: #888;
    margin: 0 0 10px;
  }}
  #perf-summary .workers-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }}
  #perf-summary .workers-table th {{
    text-align: left;
    padding: 7px 10px;
    background: #f0f1f4;
    color: #555;
    font-weight: 600;
    border-bottom: 2px solid #ddd;
  }}
  #perf-summary .workers-table td {{
    padding: 8px 10px;
    border-bottom: 1px solid #eee;
    color: #333;
    vertical-align: top;
  }}
  #perf-summary .workers-table td:first-child {{ font-weight: 600; color: #111; white-space: nowrap; }}
  #perf-summary .glossary {{
    font-size: 13px;
    color: #444;
    line-height: 1.7;
  }}
  #perf-summary .glossary dt {{
    font-weight: 700;
    color: #111;
    display: inline;
  }}
  #perf-summary .glossary dd {{
    display: inline;
    margin: 0;
  }}
  #perf-summary .glossary dd::after {{
    content: "";
    display: block;
    margin-bottom: 6px;
  }}
</style>

<div id="perf-summary">
  <h2>Performance Test &#8212; Summary</h2>
  <div class="meta">{start} &#8594; {end} &nbsp;&#183;&nbsp; {duration} &nbsp;&#183;&nbsp; {host}</div>
  <hr class="divider">

  <div class="overview">
    <div class="stat">
      <div class="val">{total_requests:,}</div>
      <div class="key">Total Requests</div>
    </div>
    <div class="stat">
      <div class="val">{total_failures:,}</div>
      <div class="key">Total Failures</div>
    </div>
    <div class="stat">
      <div class="val" style="font-size:18px">{_status(overall_fpct)}</div>
      <div class="key">Overall Status</div>
    </div>
  </div>

  <table>
    <thead>
      <tr>
        <th>API</th>
        <th>Requests</th>
        <th>Failures</th>
        <th>p50 (median)</th>
        <th>p99</th>
        <th>Worst</th>
        <th>Status</th>
      </tr>
    </thead>
    <tbody>{api_rows_html}
    </tbody>
  </table>

  <hr class="divider" style="margin: 28px 0 20px;">

  <div class="two-col">
    <div>
      <h3>Who was simulated</h3>
      <table class="workers-table">
        <thead>
          <tr><th>Workers</th><th>Count</th><th>Call frequency</th><th>API called</th><th>Approx. rate</th></tr>
        </thead>
        <tbody>
          <tr>
            <td>Tablet (scan workers)</td>
            <td>20</td>
            <td>1 scan every 40s per worker</td>
            <td>POST /scans</td>
            <td>20 &#xF7; 40s = <strong>0.5 scans/s</strong><br><span style="color:#999;font-size:12px">~30 scans/min total</span></td>
          </tr>
          <tr>
            <td>Home screen users</td>
            <td>5</td>
            <td rowspan="4" style="vertical-align:middle">1 rollup + 1 scans call on <strong>every</strong> scan push</td>
            <td rowspan="4" style="vertical-align:middle">GET /datasetSync [DAILY_ROLLUP_BY_MENUS]<br>GET /datasetSync [SCANS]</td>
            <td rowspan="4" style="vertical-align:middle;text-align:center">Per scan: 20 rollup + 20 scans = <strong>40 calls</strong><br><span style="color:#999;font-size:12px">At 0.5 scans/s &rarr; 10 rollup/s + 10 scans/s</span></td>
          </tr>
          <tr>
            <td>Live View users</td>
            <td>5</td>
          </tr>
          <tr>
            <td>Manage screen users</td>
            <td>5</td>
          </tr>
          <tr>
            <td>Scan Log users</td>
            <td>5</td>
          </tr>
        </tbody>
      </table>

      <div style="margin-top:14px;padding:12px 16px;background:#f5f6f8;border-radius:8px;font-size:13px;color:#555;line-height:1.7">
        <strong style="color:#111">How the flow works:</strong><br>
        A tablet inserts a scan &rarr; server fires a WebSocket push (<code>dataset-sync-changed</code>) to all 20 connected app users &rarr;
        each app user immediately fires <strong>both</strong> a rollup call and a scans call in parallel &rarr; user sees updated numbers on screen.<br>
        Every single scan push results in <strong>20 rollup + 20 scans = 40 simultaneous HTTP calls</strong> hitting the server.
        With 20 tablet workers each inserting 1 scan every 40s, all 20 scans land in a burst every 40s,
        producing <strong>800 follow-up calls</strong> (400 rollup + 400 scans) within seconds of each burst.
      </div>
    </div>

    <div>
      <h3>How to read the numbers</h3>
      <dl class="glossary">
        <dt>Failures</dt>
        <dd> &#8212; Requests where the server returned an error or an empty response. A failure means the app would have shown stale or missing data to the user.</dd>
        <dt>p50 (median)</dt>
        <dd> &#8212; Half of all requests completed faster than this. A good indicator of typical day-to-day speed.</dd>
        <dt>p99</dt>
        <dd> &#8212; 99% of requests completed faster than this. Reflects what a user experiences on a slow moment.</dd>
        <dt>Worst</dt>
        <dd> &#8212; The single slowest request recorded during the entire test. An outlier &#8212; not representative of normal usage, but useful for spotting extreme spikes.</dd>
      </dl>

    </div>
  </div>
</div>
"""


def inject(html_path: Path, summary_html: str, out_path: Path):
    content = html_path.read_text(encoding="utf-8")
    # inject before <div id="root"> — avoids touching the JS bundle
    injected = content.replace('<div id="root">', summary_html + '<div id="root">', 1)
    out_path.write_text(injected, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", default="reports/performance/locust_report.html")
    parser.add_argument("--out",  default="reports/performance/locust_report_summary.html")
    args = parser.parse_args()

    html_path = Path(args.html)
    out_path  = Path(args.out)

    if not html_path.exists():
        print(f"HTML not found: {html_path}", file=sys.stderr)
        sys.exit(1)

    content = html_path.read_text(encoding="utf-8")
    data    = _extract_template_args(content)
    summary = build_summary(data)
    inject(html_path, summary, out_path)
    print(f"Summary report -> {out_path}  (original untouched)")


if __name__ == "__main__":
    main()
