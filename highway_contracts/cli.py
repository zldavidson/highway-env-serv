import argparse
import csv
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from .crawler import Fetcher, crawl
from .store import Store


def positive(value):
    value = int(value)
    if value < 1:
        raise argparse.ArgumentTypeError('Must be positive')
    return value


def main():
    parser = argparse.ArgumentParser(description='Repeatable government PDF discovery and search')
    parser.add_argument('--data-dir', default='data')
    sub = parser.add_subparsers(dest='command', required=True)
    run = sub.add_parser('crawl')
    run.add_argument('--config', default='config/sources.json')
    run.add_argument('--source', action='append', help='Repeat to select multiple sources')
    run.add_argument('--max-requests', type=positive)
    load = sub.add_parser('ingest')
    load.add_argument('manifest')
    find = sub.add_parser('search')
    find.add_argument('query')
    find.add_argument('--state')
    find.add_argument('--limit', type=positive, default=20)
    find.add_argument('--csv', type=Path)
    sub.add_parser('stats')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    store = Store(args.data_dir)
    try:
        if args.command == 'crawl':
            sources = json.loads(Path(args.config).read_text(encoding='utf-8'))
            selected = set(args.source or [s['id'] for s in sources if s.get('enabled', False)])
            unknown = selected - {s['id'] for s in sources}
            if unknown:
                parser.error(f'Unknown sources: {sorted(unknown)}')
            reports = [crawl(s, store, args.max_requests) for s in sources if s['id'] in selected]
            folder = store.root / 'runs'
            folder.mkdir(exist_ok=True)
            path = folder / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
            path.write_text(json.dumps(reports, indent=2), encoding='utf-8')
            print(json.dumps(reports, indent=2))
            print(f'Run report: {path}')
            return 1 if any(r['errors'] or r['needs_adapter_review'] for r in reports) else 0
        if args.command == 'ingest':
            from urllib.parse import urlsplit
            errors = 0
            for item in json.loads(Path(args.manifest).read_text(encoding='utf-8')):
                try:
                    fetcher = Fetcher(store, [urlsplit(item['url']).hostname])
                    body, _ = fetcher.get(item['url'])
                    if not body.startswith(b'%PDF-'):
                        raise ValueError('Not a PDF')
                    changed = store.index(body, item['url'], item.get('source', 'manifest'),
                                          item['state'], item['title'], item.get('parent_url', item['url']))
                    print(f"{'Indexed' if changed else 'Unchanged'}: {item['title']}")
                except Exception as exc:
                    errors += 1
                    logging.error('%s: %s', item.get('url'), exc)
            return int(bool(errors))
        if args.command == 'search':
            results = store.search(args.query, args.state, args.limit)
            if args.csv:
                args.csv.parent.mkdir(parents=True, exist_ok=True)
                with args.csv.open('w', newline='', encoding='utf-8') as output:
                    writer = csv.DictWriter(output, fieldnames=['title','state','page','snippet','url','path','parent_url','source'])
                    writer.writeheader()
                    writer.writerows(results)
            print(json.dumps(results, indent=2))
        if args.command == 'stats':
            print(json.dumps({'versions': store.db.execute('SELECT COUNT(*) FROM documents').fetchone()[0],
                              'current_documents': store.db.execute('SELECT COUNT(*) FROM versions').fetchone()[0],
                              'pages': store.db.execute('SELECT COUNT(*) FROM pages').fetchone()[0]}, indent=2))
        return 0
    except Exception as exc:
        logging.error('%s', exc)
        return 1
    finally:
        store.close()


if __name__ == '__main__':
    sys.exit(main())
