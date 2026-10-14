import collections
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from html.parser import HTMLParser

LOG = logging.getLogger(__name__)
AGENT = 'HighwayContractsBot/0.1'
MAX_BYTES = 50 * 1024 * 1024


def canonical(url):
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password:
        return None
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc.lower(), parts.path or '/', parts.query, ''))


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.current = [dict(attrs).get('href', ''), '']

    def handle_data(self, text):
        if self.current is not None:
            self.current[1] += text

    def handle_endtag(self, tag):
        if tag == 'a' and self.current is not None:
            self.links.append(tuple(self.current))
            self.current = None


class ScopedRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, hosts):
        self.hosts = hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = canonical(newurl)
        if not target or urllib.parse.urlsplit(target).hostname not in self.hosts:
            raise ValueError('Redirect outside configured HTTPS hosts')
        return super().redirect_request(req, fp, code, msg, headers, target)


class Fetcher:
    def __init__(self, store, hosts, delay=1.5, retries=2):
        self.store = store
        self.hosts = set(hosts)
        self.delay = delay
        self.retries = retries
        self.last = {}
        self.robots = {}
        self.opener = urllib.request.build_opener(ScopedRedirect(self.hosts))

    def raw(self, url, headers):
        host = urllib.parse.urlsplit(url).hostname
        if host not in self.hosts:
            raise ValueError('Host outside configured scope')
        for attempt in range(self.retries + 1):
            time.sleep(max(0, self.delay - (time.monotonic() - self.last.get(host, 0))))
            self.last[host] = time.monotonic()
            try:
                with self.opener.open(urllib.request.Request(url, headers=headers), timeout=45) as response:
                    body = response.read(MAX_BYTES + 1)
                    if len(body) > MAX_BYTES:
                        raise ValueError('Resource exceeds 50 MB')
                    return body, response.headers
            except urllib.error.HTTPError as exc:
                if exc.code not in (429, 500, 502, 503, 504) or attempt == self.retries:
                    raise
                retry = exc.headers.get('Retry-After', '')
                time.sleep(min(60, int(retry)) if retry.isdigit() else 2 ** attempt)
            except (urllib.error.URLError, TimeoutError):
                if attempt == self.retries:
                    raise
                time.sleep(2 ** attempt)

    def permitted(self, url):
        parts = urllib.parse.urlsplit(url)
        origin = f'{parts.scheme}://{parts.netloc}'
        if origin not in self.robots:
            robot = urllib.robotparser.RobotFileParser()
            try:
                body, _ = self.raw(origin + '/robots.txt', {'User-Agent': AGENT})
                robot.parse(body.decode('utf-8', errors='replace').splitlines())
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    robot.parse([])
                else:
                    raise RuntimeError(f'Cannot verify robots.txt: HTTP {exc.code}') from exc
            crawl_delay = robot.crawl_delay(AGENT)
            if crawl_delay:
                self.delay = max(self.delay, crawl_delay)
            self.robots[origin] = robot
        return self.robots[origin].can_fetch(AGENT, url)

    def get(self, url):
        if not self.permitted(url):
            raise PermissionError('Disallowed by robots.txt')
        cached = self.store.cached(url)
        headers = {'User-Agent': AGENT, 'Accept': 'text/html,application/pdf'}
        if cached:
            if cached[0]:
                headers['If-None-Match'] = cached[0]
            if cached[1]:
                headers['If-Modified-Since'] = cached[1]
        try:
            body, response = self.raw(url, headers)
        except urllib.error.HTTPError as exc:
            if exc.code == 304 and cached:
                return cached[2], cached[3]
            raise
        content_type = response.get('Content-Type', '')
        self.store.cache(url, response.get('ETag'), response.get('Last-Modified'), body, content_type)
        return body, content_type


def crawl(source, store, max_requests=None):
    fetcher = Fetcher(store, source['allowed_hosts'], source.get('delay_seconds', 1.5))
    queue = collections.deque((url, 0, source['name'], url) for url in source['start_urls'])
    seen = set()
    report = {'source': source['id'], 'fetched': 0, 'indexed': 0, 'unchanged': 0,
              'html_pages': 0, 'errors': [], 'truncated': False}
    budget = max_requests or source.get('max_requests', 40)
    while queue and report['fetched'] < budget:
        raw_url, depth, title, parent = queue.popleft()
        url = canonical(raw_url)
        if not url or url in seen:
            continue
        seen.add(url)
        report['fetched'] += 1
        try:
            LOG.info('%s %s', source['id'], url)
            body, kind = fetcher.get(url)
            if body.startswith(b'%PDF-'):
                changed = store.index(body, url, source['id'], source['state'], title.strip() or url, parent)
                report['indexed' if changed else 'unchanged'] += 1
            elif 'text/html' in kind:
                report['html_pages'] += 1
                if depth >= source.get('max_depth', 2):
                    continue
                parser = Links()
                parser.feed(body.decode('utf-8', errors='replace'))
                for href, text in parser.links:
                    target = canonical(urllib.parse.urljoin(url, href))
                    if not target or urllib.parse.urlsplit(target).hostname not in fetcher.hosts:
                        continue
                    haystack = (target + ' ' + text).lower()
                    attachment = '.pdf' in haystack or 'filedownload' in target.lower()
                    path = urllib.parse.urlsplit(target).path
                    page_allowed = any(path.startswith(prefix) for prefix in source.get('page_path_prefixes', ['/']))
                    relevant = any(term.lower() in haystack for term in source['follow_terms'])
                    if attachment and relevant or page_allowed and relevant:
                        queue.append((target, depth + 1, text, url))
            else:
                raise ValueError(f'Unsupported response type: {kind}')
        except Exception as exc:
            LOG.warning('%s: %s', url, exc)
            report['errors'].append({'url': url, 'error': str(exc)})
    report['truncated'] = bool(queue)
    report['needs_adapter_review'] = report['indexed'] + report['unchanged'] == 0
    return report
