import hashlib
import json
import sqlite3
from pathlib import Path

from pypdf import PdfReader


class Store:
    def __init__(self, directory):
        self.root = Path(directory).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / 'pdfs').mkdir(exist_ok=True)
        self.db = sqlite3.connect(self.root / 'crawler.sqlite')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS resources (
                url TEXT PRIMARY KEY, etag TEXT, modified TEXT, body BLOB,
                content_type TEXT, checked_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY, url TEXT, source TEXT, state TEXT,
                title TEXT, parent_url TEXT, path TEXT, ocr_pages TEXT,
                indexed_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS versions (
                source TEXT, url TEXT, document_id TEXT,
                PRIMARY KEY(source,url));
            CREATE VIRTUAL TABLE IF NOT EXISTS pages USING fts5(
                document_id UNINDEXED, page UNINDEXED, text);
        ''')

    def cached(self, url):
        return self.db.execute('SELECT etag,modified,body,content_type FROM resources WHERE url=?', (url,)).fetchone()

    def cache(self, url, etag, modified, body, content_type):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO resources VALUES (?,?,?,?,?,CURRENT_TIMESTAMP)',
                            (url, etag, modified, body, content_type))

    def index(self, content, url, source, state, title, parent_url):
        digest = hashlib.sha256(content).hexdigest()
        identity = hashlib.sha256(f'{source}\n{url}\n{digest}'.encode()).hexdigest()
        if self.db.execute('SELECT 1 FROM documents WHERE id=?', (identity,)).fetchone():
            with self.db:
                self.db.execute('INSERT OR REPLACE INTO versions VALUES (?,?,?)', (source, url, identity))
            return False
        path = self.root / 'pdfs' / f'{digest}.pdf'
        temporary = path.with_suffix('.part')
        temporary.write_bytes(content)
        temporary.replace(path)
        reader = PdfReader(path)
        extracted = [(number, page.extract_text() or '') for number, page in enumerate(reader.pages, 1)]
        review = [number for number, text in extracted if len(text.strip()) < 30]
        with self.db:
            self.db.execute('INSERT INTO documents(id,url,source,state,title,parent_url,path,ocr_pages) VALUES (?,?,?,?,?,?,?,?)',
                            (identity, url, source, state, title, parent_url, str(path), json.dumps(review)))
            self.db.executemany('INSERT INTO pages VALUES (?,?,?)', [(identity, n, text) for n, text in extracted])
            self.db.execute('INSERT OR REPLACE INTO versions VALUES (?,?,?)', (source, url, identity))
        return True

    def search(self, query, state=None, limit=20):
        sql = '''SELECT d.title,d.state,p.page,snippet(pages,2,'[',']',' ... ',30),
                 d.url,d.path,d.parent_url,d.source FROM pages p
                 JOIN documents d ON d.id=p.document_id
                 JOIN versions v ON v.document_id=d.id
                 WHERE pages MATCH ?'''
        params = [query]
        if state:
            sql += ' AND d.state=?'
            params.append(state.upper())
        sql += ' ORDER BY bm25(pages) LIMIT ?'
        params.append(limit)
        keys = ['title', 'state', 'page', 'snippet', 'url', 'path', 'parent_url', 'source']
        return [dict(zip(keys, row)) for row in self.db.execute(sql, params)]

    def close(self):
        self.db.close()
