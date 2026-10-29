"""Run tests/tests.html in headless Edge or Chrome and print the results.

Usage:  python tests/run_tests.py            (exit code 0 = all passed)
        python tests/run_tests.py --browser "C:/path/to/chrome.exe"

It starts its own local server on a free port, so it never touches the save you play with on port 8765.
"""
import argparse, html, json, os, re, shutil, socket, subprocess, sys, tempfile, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANDIDATES = [
    os.environ.get('BROWSER', ''),
    r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
    shutil.which('google-chrome') or '', shutil.which('chromium') or '', shutil.which('microsoft-edge') or '',
]


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--browser', help='path to a Chromium-based browser')
    ap.add_argument('--budget', type=int, default=240000, help='virtual time budget in ms')
    a = ap.parse_args()
    browser = next((b for b in [a.browser] + CANDIDATES if b and os.path.exists(b)), None)
    if not browser:
        print('No Edge/Chrome found. Pass --browser PATH or open tests/tests.html through a local server.')
        return 2

    port = free_port()
    server = subprocess.Popen([sys.executable, '-m', 'http.server', str(port), '--bind', '127.0.0.1'], cwd=ROOT,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    profile = tempfile.mkdtemp(prefix='fs-tests-')
    try:
        url = 'http://127.0.0.1:%d/tests/tests.html' % port
        for _ in range(50):                          # wait for the server
            try:
                urllib.request.urlopen(url, timeout=1); break
            except Exception:
                time.sleep(.1)
        t0 = time.time()
        out = subprocess.run([browser, '--headless=new', '--disable-gpu', '--no-first-run', '--mute-audio', '--window-size=900,900',
                              '--user-data-dir=' + profile, '--virtual-time-budget=%d' % a.budget, '--dump-dom', url],
                             capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=900).stdout
        m = re.search(r'<pre id="out">(.*?)</pre>', out, re.S)
        if not m or not m.group(1).strip():
            print('The tests did not finish (no results in the page). Try a larger --budget, or open tests/tests.html in a browser.')
            return 1
        res = json.loads(html.unescape(m.group(1)))
        for r in res['results']:
            print(('  PASS  ' if r['ok'] else '  FAIL  ') + r['name'] + ('' if r['ok'] else '\n        ' + r['msg']))
        print('\n%d / %d passed in %.1f s' % (res['pass'], res['total'], time.time() - t0))
        return 0 if res['pass'] == res['total'] else 1
    finally:
        server.terminate()
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
