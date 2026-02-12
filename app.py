"""
ArchGraph - 建筑灵感知识图谱
FastAPI 后端：案例管理 / URL导入 / AI灵感搜索 / 图谱数据 / 图片上传
"""
from dotenv import load_dotenv
load_dotenv()
import json, uuid, os, re, shutil
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager
from functools import lru_cache
from datetime import datetime, timedelta

import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from openai import OpenAI

# —— Config ——
USE_DATABASE = os.getenv("USE_DATABASE", "false").lower() == "true"  # 默认使用JSON
DB_FILE = Path("archgraph.db")
DATA_FILE = Path("data.json")
SEED_FILE = Path("seed_data.json")
TAGS_FILE = Path("tags.json")
CONCEPTS_FILE = Path("concepts.json")
NEBULAS_FILE = Path("nebulas.json")
HISTORY_FILE = Path("history.json")
SNAPSHOTS_DIR = Path("snapshots")
SNAPSHOTS_DIR.mkdir(exist_ok=True)

# —— Performance Cache ——
_graph_cache = None
_graph_cache_time = None
CACHE_TTL = timedelta(seconds=5)  # 5秒缓存

def _get_cached_graph(active_nebula_id: Optional[str] = None):
    """获取缓存的图谱数据"""
    global _graph_cache, _graph_cache_time
    cache_key = f"graph_{active_nebula_id or 'all'}"
    if _graph_cache_time and datetime.now() - _graph_cache_time < CACHE_TTL:
        if cache_key in _graph_cache:
            return _graph_cache[cache_key]
    return None

def _set_cached_graph(active_nebula_id: Optional[str] = None, graph_data: dict = None):
    """设置缓存的图谱数据"""
    global _graph_cache, _graph_cache_time
    if _graph_cache is None:
        _graph_cache = {}
    cache_key = f"graph_{active_nebula_id or 'all'}"
    _graph_cache[cache_key] = graph_data
    _graph_cache_time = datetime.now()

def _invalidate_graph_cache():
    """使图谱缓存失效"""
    global _graph_cache, _graph_cache_time
    _graph_cache = None
    _graph_cache_time = None
UPLOAD_DIR = Path("static/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# —— Database layer (optional SQLite support) ——
if USE_DATABASE:
    import sqlite3
    def _init_db():
        """初始化SQLite数据库"""
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS cases (
            id TEXT PRIMARY KEY,
            name TEXT,
            architect TEXT,
            year TEXT,
            location TEXT,
            tags TEXT,
            description TEXT,
            image_url TEXT,
            source_url TEXT,
            data TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS concepts (
            id TEXT PRIMARY KEY,
            name TEXT,
            keywords TEXT,
            description TEXT,
            image_url TEXT,
            source_url TEXT,
            data TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS tags (
            id TEXT PRIMARY KEY,
            name TEXT,
            parent_id TEXT,
            parent_ids TEXT,
            parent_details TEXT,
            children TEXT,
            data TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS nebulas (
            id TEXT PRIMARY KEY,
            name TEXT,
            case_ids TEXT,
            concept_ids TEXT,
            data TEXT
        )''')
        conn.commit()
        conn.close()
    _init_db()

    def _db_load_cases() -> list[dict]:
        """从数据库加载案例"""
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT * FROM cases")
        rows = c.fetchall()
        conn.close()
        cases = []
        for row in rows:
            case = json.loads(row[9]) if row[9] else {}
            case.update({
                "id": row[0], "name": row[1], "architect": row[2], "year": row[3],
                "location": row[4], "tags": json.loads(row[5]) if row[5] else [],
                "description": row[6], "image_url": row[7], "source_url": row[8]
            })
            cases.append(case)
        return cases

    def _db_save_cases(cases: list[dict]):
        """保存案例到数据库"""
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("DELETE FROM cases")
        for case in cases:
            c.execute("INSERT INTO cases VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (case.get("id"), case.get("name"), case.get("architect"), case.get("year"),
                 case.get("location"), json.dumps(case.get("tags", [])), case.get("description"),
                 case.get("image_url"), case.get("source_url"), json.dumps(case)))
        conn.commit()
        conn.close()

    def _db_load_concepts() -> list[dict]:
        """从数据库加载概念"""
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT * FROM concepts")
        rows = c.fetchall()
        conn.close()
        concepts = []
        for row in rows:
            concept = json.loads(row[6]) if row[6] else {}
            concept.update({
                "id": row[0], "name": row[1], "keywords": row[2], "description": row[3],
                "image_url": row[4], "source_url": row[5]
            })
            concepts.append(concept)
        return concepts

    def _db_save_concepts(concepts: list[dict]):
        """保存概念到数据库"""
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("DELETE FROM concepts")
        for concept in concepts:
            c.execute("INSERT INTO concepts VALUES (?, ?, ?, ?, ?, ?, ?)",
                (concept.get("id"), concept.get("name"), concept.get("keywords"),
                 concept.get("description"), concept.get("image_url"), concept.get("source_url"),
                 json.dumps(concept)))
        conn.commit()
        conn.close()

    def _db_load_tags() -> dict:
        """从数据库加载标签"""
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT * FROM tags")
        rows = c.fetchall()
        conn.close()
        tags = {}
        for row in rows:
            tag = json.loads(row[6]) if row[6] else {}
            tag.update({
                "id": row[0], "name": row[1], "parent_id": row[2],
                "parent_ids": json.loads(row[3]) if row[3] else [],
                "parent_details": json.loads(row[4]) if row[4] else [],
                "children": json.loads(row[5]) if row[5] else []
            })
            tags[row[0]] = tag
        return tags

    def _db_save_tags(tags: dict):
        """保存标签到数据库"""
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("DELETE FROM tags")
        for tid, tag in tags.items():
            c.execute("INSERT INTO tags VALUES (?, ?, ?, ?, ?, ?, ?)",
                (tid, tag.get("name"), tag.get("parent_id"),
                 json.dumps(tag.get("parent_ids", [])), json.dumps(tag.get("parent_details", [])),
                 json.dumps(tag.get("children", [])), json.dumps(tag)))
        conn.commit()
        conn.close()

    def _db_load_nebulas() -> list[dict]:
        """从数据库加载星云"""
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT * FROM nebulas")
        rows = c.fetchall()
        conn.close()
        nebulas = []
        for row in rows:
            nebula = json.loads(row[4]) if row[4] else {}
            nebula.update({
                "id": row[0], "name": row[1],
                "case_ids": json.loads(row[2]) if row[2] else [],
                "concept_ids": json.loads(row[3]) if row[3] else []
            })
            nebulas.append(nebula)
        return nebulas

    def _db_save_nebulas(nebulas: list[dict]):
        """保存星云到数据库"""
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("DELETE FROM nebulas")
        for nebula in nebulas:
            c.execute("INSERT INTO nebulas VALUES (?, ?, ?, ?, ?)",
                (nebula.get("id"), nebula.get("name"),
                 json.dumps(nebula.get("case_ids", [])), json.dumps(nebula.get("concept_ids", [])),
                 json.dumps(nebula)))
        conn.commit()
        conn.close()

client = OpenAI(
    api_key=os.getenv("LLM_API_KEY", "sk-xxx"),
    base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
)
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
ENABLE_IMAGE_GENERATION = os.getenv("ENABLE_IMAGE_GENERATION", "true").lower() == "true"
IMAGE_GENERATION_PROVIDER = os.getenv("IMAGE_GENERATION_PROVIDER", "openai").lower()  # openai 或 doubao
DOUBAO_IMAGE_API_KEY = os.getenv("DOUBAO_IMAGE_API_KEY", "")
DOUBAO_IMAGE_API_URL = os.getenv("DOUBAO_IMAGE_API_URL", "https://ark.cn-beijing.volces.com/api/v3/images/generations")

# —— Database layer (optional SQLite support) ——
if USE_DATABASE:
    import sqlite3
    def _init_db():
        """初始化SQLite数据库"""
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS cases (
            id TEXT PRIMARY KEY,
            name TEXT,
            architect TEXT,
            year TEXT,
            location TEXT,
            tags TEXT,
            description TEXT,
            image_url TEXT,
            source_url TEXT,
            data TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS concepts (
            id TEXT PRIMARY KEY,
            name TEXT,
            keywords TEXT,
            description TEXT,
            image_url TEXT,
            source_url TEXT,
            data TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS tags (
            id TEXT PRIMARY KEY,
            name TEXT,
            parent_id TEXT,
            parent_ids TEXT,
            parent_details TEXT,
            children TEXT,
            data TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS nebulas (
            id TEXT PRIMARY KEY,
            name TEXT,
            case_ids TEXT,
            concept_ids TEXT,
            data TEXT
        )''')
        conn.commit()
        conn.close()
    _init_db()

def _db_load_cases() -> list[dict]:
    """从数据库加载案例"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM cases")
    rows = c.fetchall()
    conn.close()
    cases = []
    for row in rows:
        case = json.loads(row[9]) if row[9] else {}
        case.update({
            "id": row[0], "name": row[1], "architect": row[2], "year": row[3],
            "location": row[4], "tags": json.loads(row[5]) if row[5] else [],
            "description": row[6], "image_url": row[7], "source_url": row[8]
        })
        cases.append(case)
    return cases

def _db_save_cases(cases: list[dict]):
    """保存案例到数据库"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM cases")
    for case in cases:
        c.execute("INSERT INTO cases VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (case.get("id"), case.get("name"), case.get("architect"), case.get("year"),
             case.get("location"), json.dumps(case.get("tags", [])), case.get("description"),
             case.get("image_url"), case.get("source_url"), json.dumps(case)))
    conn.commit()
    conn.close()

def _db_load_concepts() -> list[dict]:
    """从数据库加载概念"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM concepts")
    rows = c.fetchall()
    conn.close()
    concepts = []
    for row in rows:
        concept = json.loads(row[6]) if row[6] else {}
        concept.update({
            "id": row[0], "name": row[1], "keywords": row[2], "description": row[3],
            "image_url": row[4], "source_url": row[5]
        })
        concepts.append(concept)
    return concepts

def _db_save_concepts(concepts: list[dict]):
    """保存概念到数据库"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM concepts")
    for concept in concepts:
        c.execute("INSERT INTO concepts VALUES (?, ?, ?, ?, ?, ?, ?)",
            (concept.get("id"), concept.get("name"), concept.get("keywords"),
             concept.get("description"), concept.get("image_url"), concept.get("source_url"),
             json.dumps(concept)))
    conn.commit()
    conn.close()

def _db_load_tags() -> dict:
    """从数据库加载标签"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM tags")
    rows = c.fetchall()
    conn.close()
    tags = {}
    for row in rows:
        tag = json.loads(row[6]) if row[6] else {}
        tag.update({
            "id": row[0], "name": row[1], "parent_id": row[2],
            "parent_ids": json.loads(row[3]) if row[3] else [],
            "parent_details": json.loads(row[4]) if row[4] else [],
            "children": json.loads(row[5]) if row[5] else []
        })
        tags[row[0]] = tag
    return tags

def _db_save_tags(tags: dict):
    """保存标签到数据库"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM tags")
    for tid, tag in tags.items():
        c.execute("INSERT INTO tags VALUES (?, ?, ?, ?, ?, ?, ?)",
            (tid, tag.get("name"), tag.get("parent_id"),
             json.dumps(tag.get("parent_ids", [])), json.dumps(tag.get("parent_details", [])),
             json.dumps(tag.get("children", [])), json.dumps(tag)))
    conn.commit()
    conn.close()

def _db_load_nebulas() -> list[dict]:
    """从数据库加载星云"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM nebulas")
    rows = c.fetchall()
    conn.close()
    nebulas = []
    for row in rows:
        nebula = json.loads(row[4]) if row[4] else {}
        nebula.update({
            "id": row[0], "name": row[1],
            "case_ids": json.loads(row[2]) if row[2] else [],
            "concept_ids": json.loads(row[3]) if row[3] else []
        })
        nebulas.append(nebula)
    return nebulas

def _db_save_nebulas(nebulas: list[dict]):
    """保存星云到数据库"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM nebulas")
    for nebula in nebulas:
        c.execute("INSERT INTO nebulas VALUES (?, ?, ?, ?, ?)",
            (nebula.get("id"), nebula.get("name"),
             json.dumps(nebula.get("case_ids", [])), json.dumps(nebula.get("concept_ids", [])),
             json.dumps(nebula)))
    conn.commit()
    conn.close()

# —— Data layer ——
def load_cases() -> list[dict]:
    if USE_DATABASE:
        return _db_load_cases()
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    if SEED_FILE.exists():
        cases = json.loads(SEED_FILE.read_text(encoding="utf-8"))
        save_cases(cases)
        # 创建默认星云"示范案例"，包含所有种子案例
        _create_default_nebula(cases)
        return cases
    return []

def save_cases(cases: list[dict]):
    if USE_DATABASE:
        _db_save_cases(cases)
    else:
        DATA_FILE.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
    _invalidate_graph_cache()

def load_tags() -> dict:
    if USE_DATABASE:
        return _db_load_tags()
    if TAGS_FILE.exists():
        return json.loads(TAGS_FILE.read_text(encoding="utf-8"))
    return {}

def save_tags(tags: dict):
    if USE_DATABASE:
        _db_save_tags(tags)
    else:
        TAGS_FILE.write_text(json.dumps(tags, ensure_ascii=False, indent=2), encoding="utf-8")
    _invalidate_graph_cache()

def load_concepts() -> list[dict]:
    if USE_DATABASE:
        return _db_load_concepts()
    if CONCEPTS_FILE.exists():
        return json.loads(CONCEPTS_FILE.read_text(encoding="utf-8"))
    return []

def save_concepts(concepts: list[dict]):
    if USE_DATABASE:
        _db_save_concepts(concepts)
    else:
        CONCEPTS_FILE.write_text(json.dumps(concepts, ensure_ascii=False, indent=2), encoding="utf-8")
    _invalidate_graph_cache()

def load_nebulas() -> list[dict]:
    if NEBULAS_FILE.exists():
        nebulas = json.loads(NEBULAS_FILE.read_text(encoding="utf-8"))
        # 如果存在种子案例但还没有默认星云，则创建
        if DATA_FILE.exists() and not any(n.get("name") == "示范案例" for n in nebulas):
            cases = load_cases()
            # 检查是否有种子案例（ID格式为case_001到case_012）
            seed_case_ids = [c["id"] for c in cases if c["id"].startswith("case_00")]
            if seed_case_ids:
                default_nebula = {
                    "id": "nebula_demo",
                    "name": "示范案例",
                    "case_ids": seed_case_ids,
                    "concept_ids": []
                }
                nebulas.append(default_nebula)
                save_nebulas(nebulas)
        return nebulas
    return []

def save_nebulas(nebulas: list[dict]):
    if USE_DATABASE:
        _db_save_nebulas(nebulas)
    else:
        NEBULAS_FILE.write_text(json.dumps(nebulas, ensure_ascii=False, indent=2), encoding="utf-8")
    _invalidate_graph_cache()

def _create_default_nebula(seed_cases: list[dict]):
    """创建默认星云'示范案例'，包含所有种子案例。如果已存在则不重复创建。"""
    nebulas = load_nebulas()
    # 检查是否已存在名为"示范案例"的星云
    if any(n.get("name") == "示范案例" for n in nebulas):
        return
    # 获取所有种子案例的ID
    seed_case_ids = [c["id"] for c in seed_cases]
    default_nebula = {
        "id": "nebula_demo",
        "name": "示范案例",
        "case_ids": seed_case_ids,
        "concept_ids": []
    }
    nebulas.append(default_nebula)
    save_nebulas(nebulas)


def ensure_tag_by_name(name: str) -> str:
    """确保标签名在 tags 中存在，不存在则创建为根节点。返回 tag_id。"""
    if not name or not name.strip():
        return ""
    name = name.strip()
    tags = load_tags()
    for tid, td in tags.items():
        if td.get("name") == name:
            return tid
    tag_id = f"tag_{uuid.uuid4().hex[:8]}"
    tags[tag_id] = {
        "id": tag_id,
        "name": name,
        "parent_id": None,
        "parent_ids": [],
        "parent_details": [],
        "children": [],
    }
    save_tags(tags)
    return tag_id


def sync_case_tags_to_registry(case: dict):
    """将案例的 tags 同步到 tags.json，保证每个标签名都有对应节点。"""
    for tag_name in case.get("tags") or []:
        ensure_tag_by_name(tag_name)

# —— Pydantic models ——
class CaseCreate(BaseModel):
    name: str
    architect: str = ""
    year: str = ""
    location: str = ""
    tags: list[str] = []
    description: str = ""
    image_url: str = ""
    source_url: str = ""

class URLImport(BaseModel):
    url: str
    extra_notes: str = ""

class InspirationQuery(BaseModel):
    query: str
    selected_tags: list[str] = []

class HybridizeRequest(BaseModel):
    case_ids: list[str]
    dimensions: list[str]
    case_dimensions: Optional[dict[str, list[str]]] = None  # 每个案例对应的维度

class CaseUpdate(BaseModel):
    name: Optional[str] = None
    architect: Optional[str] = None
    year: Optional[str] = None
    location: Optional[str] = None
    tags: Optional[list[str]] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    source_url: Optional[str] = None

class TagCreate(BaseModel):
    name: str
    parent_id: Optional[str] = None
    parent_ids: Optional[list[str]] = None

class TagUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[str] = None
    parent_ids: Optional[list[str]] = None

class ConceptCreate(BaseModel):
    name: str
    keywords: list[str] = []
    description: str = ""
    image_url: str = ""
    source_url: str = ""

class ConceptUpdate(BaseModel):
    name: Optional[str] = None
    keywords: Optional[list[str]] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    source_url: Optional[str] = None

class NebulaCreate(BaseModel):
    name: str
    case_ids: list[str] = []
    concept_ids: list[str] = []

class NebulaUpdate(BaseModel):
    name: Optional[str] = None
    case_ids: Optional[list[str]] = None
    concept_ids: Optional[list[str]] = None

# —— App ——
@asynccontextmanager
async def lifespan(app: FastAPI):
    load_cases()
    yield

app = FastAPI(title="ArchGraph API", lifespan=lifespan)

# —— Image Upload ——
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

@app.post("/api/upload-image")
async def upload_image(file: UploadFile = File(...)):
    """上传图片，返回可访问的URL路径"""
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, f"不支持的图片格式: {ext}")
    fname = f"{uuid.uuid4().hex[:12]}{ext}"
    fpath = UPLOAD_DIR / fname
    with open(fpath, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"url": f"/static/uploads/{fname}"}

@app.post("/api/upload-image-for-case/{case_id}")
async def upload_image_for_case(case_id: str, file: UploadFile = File(...)):
    """上传图片并直接关联到案例"""
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, f"不支持的图片格式: {ext}")
    fname = f"{case_id}_{uuid.uuid4().hex[:8]}{ext}"
    fpath = UPLOAD_DIR / fname
    with open(fpath, "wb") as f:
        shutil.copyfileobj(file.file, f)
    url = f"/static/uploads/{fname}"
    cases = load_cases()
    for c in cases:
        if c["id"] == case_id:
            c["image_url"] = url
            save_cases(cases)
            return {"url": url, "case": c}
    raise HTTPException(404, "Case not found")

# —— Case CRUD ——
@app.get("/api/cases")
def list_cases():
    return load_cases()

@app.post("/api/cases")
def create_case(case: CaseCreate):
    _record_history("create_case", {"case_name": case.name})
    cases = load_cases()
    new_case = {"id": f"case_{uuid.uuid4().hex[:8]}", **case.model_dump()}
    cases.append(new_case)
    save_cases(cases)
    sync_case_tags_to_registry(new_case)
    return new_case

@app.put("/api/cases/{case_id}")
def update_case(case_id: str, update: CaseUpdate):
    _record_history("update_case", {"case_id": case_id})
    cases = load_cases()
    for c in cases:
        if c["id"] == case_id:
            for k, v in update.model_dump(exclude_none=True).items():
                c[k] = v
            save_cases(cases)
            sync_case_tags_to_registry(c)
            return c
    raise HTTPException(404, "Case not found")

@app.delete("/api/cases/{case_id}")
def delete_case(case_id: str):
    _record_history("delete_case", {"case_id": case_id})
    cases = load_cases()
    cases = [c for c in cases if c["id"] != case_id]
    save_cases(cases)
    return {"ok": True}

# —— URL Import (improved image scraping) ——
async def _fetch_best_image(soup, url: str) -> str:
    """从网页中提取最佳代表性图片"""
    from urllib.parse import urlparse, urljoin

    candidates = []

    # 1. Open Graph image (最高优先级)
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        candidates.append(("og", og["content"]))

    # 2. Twitter card image
    tw = soup.find("meta", attrs={"name": "twitter:image"})
    if tw and tw.get("content"):
        candidates.append(("tw", tw["content"]))

    # 3. 文章主图 (ArchDaily / gooood 等常见结构)
    for sel in [
        "article img", ".gallery img", ".project-image img",
        ".post-content img", "figure img", ".entry-content img",
        ".main-image img", "[data-src]", ".slide img",
    ]:
        imgs = soup.select(sel)
        for img in imgs[:3]:
            src = img.get("data-src") or img.get("data-lazy-src") or img.get("src") or ""
            if src:
                candidates.append(("article", src))

    # 4. 所有大图 fallback
    for img in soup.find_all("img", src=True):
        src = img["src"]
        w = img.get("width", "")
        h = img.get("height", "")
        try:
            if (w and int(w) >= 400) or (h and int(h) >= 300):
                candidates.append(("size", src))
        except ValueError:
            pass
        if any(kw in src.lower() for kw in ["hero", "cover", "feature", "main", "header", "banner"]):
            candidates.append(("keyword", src))

    # 5. 所有带图片扩展名的 img
    for img in soup.find_all("img", src=True):
        src = img["src"]
        if any(src.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
            candidates.append(("ext", src))

    # 去重 & 修正相对路径
    seen = set()
    result = []
    for priority, src in candidates:
        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("/"):
            parsed = urlparse(url)
            src = f"{parsed.scheme}://{parsed.netloc}{src}"
        elif not src.startswith("http"):
            src = urljoin(url, src)
        # 过滤掉 svg / icon / logo / 太小的占位图
        low = src.lower()
        if any(skip in low for skip in [".svg", "logo", "icon", "avatar", "favicon", "1x1", "pixel", "spacer"]):
            continue
        if src not in seen:
            seen.add(src)
            result.append(src)

    return result[0] if result else ""


async def _download_image(img_url: str) -> str:
    """下载远程图片到本地 uploads 目录，返回本地路径"""
    if not img_url:
        return ""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            "Referer": base_url if base_url else "",
        }
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as http:
            resp = await http.get(img_url, headers=headers)
            resp.raise_for_status()
            ct = resp.headers.get("content-type", "")
            if "jpeg" in ct or "jpg" in ct:
                ext = ".jpg"
            elif "png" in ct:
                ext = ".png"
            elif "webp" in ct:
                ext = ".webp"
            elif "gif" in ct:
                ext = ".gif"
            else:
                # 从 URL 推断
                for e in [".jpg", ".jpeg", ".png", ".webp"]:
                    if e in img_url.lower():
                        ext = e
                        break
                else:
                    ext = ".jpg"
            fname = f"import_{uuid.uuid4().hex[:10]}{ext}"
            fpath = UPLOAD_DIR / fname
            fpath.write_bytes(resp.content)
            return f"/static/uploads/{fname}"
    except Exception:
        return img_url  # 下载失败则保留原始 URL


@app.post("/api/import-url")
async def import_from_url(req: URLImport):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
    }
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as http:
            resp = await http.get(req.url, headers=headers)
            resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            raise HTTPException(400, f"无法访问该链接（网站拒绝访问，可能是反爬虫机制）。建议：1) 手动添加案例；2) 尝试其他来源链接；3) 检查链接是否需要登录。错误详情: {e}")
        raise HTTPException(400, f"无法访问该链接: HTTP {e.response.status_code}")
    except Exception as e:
        raise HTTPException(400, f"无法访问该链接: {e}")

    soup = BeautifulSoup(resp.text, "html.parser")

    # 提取代表性图片
    best_image_url = await _fetch_best_image(soup, req.url)

    # 尝试下载图片到本地
    local_image = await _download_image(best_image_url)

    # 提取文本
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)[:6000]

    extra = f"\n用户备注: {req.extra_notes}" if req.extra_notes else ""
    prompt = f"""请从以下网页内容中提取建筑案例信息。如果页面包含多个案例，只提取最主要的一个。
请严格按照JSON格式返回，不要包含其他文字：

{{
  "name": "项目名称",
  "architect": "建筑师/事务所",
  "year": "建成年份",
  "location": "所在城市",
  "tags": ["标签1", "标签2", "标签3", "标签4", "标签5"],
  "description": "用2-3句话描述这个项目的核心设计策略和亮点，重点说它做了什么、为什么这么做、效果如何"
}}

tags要求：提取5-8个有意义的标签，涵盖建筑风格、材料、空间策略、功能类型、设计理念等维度。
description要求：不要泛泛而谈，要有具体的设计手法和空间特点。
{extra}

网页内容：
{text}"""

    try:
        completion = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "你是一个建筑学专业助手，擅长分析和归纳建筑案例。请只返回JSON，不要添加任何其他文字或markdown格式。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )
        raw = completion.choices[0].message.content.strip()
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
        info = json.loads(raw)
    except Exception as e:
        raise HTTPException(500, f"AI 提取失败: {e}")

    cases = load_cases()
    new_case = {
        "id": f"case_{uuid.uuid4().hex[:8]}",
        "name": info.get("name", "未命名"),
        "architect": info.get("architect", ""),
        "year": info.get("year", ""),
        "location": info.get("location", ""),
        "tags": info.get("tags", []),
        "description": info.get("description", ""),
        "image_url": local_image,
        "source_url": req.url,
    }
    cases.append(new_case)
    save_cases(cases)
    return new_case

# —— Concept Management ——
@app.get("/api/concepts")
def list_concepts():
    return load_concepts()

@app.post("/api/concepts")
def create_concept(concept: ConceptCreate):
    _record_history("create_concept", {"concept_name": concept.name})
    concepts = load_concepts()
    new_concept = {"id": f"concept_{uuid.uuid4().hex[:8]}", **concept.model_dump()}
    concepts.append(new_concept)
    save_concepts(concepts)
    return new_concept

@app.put("/api/concepts/{concept_id}")
def update_concept(concept_id: str, update: ConceptUpdate):
    _record_history("update_concept", {"concept_id": concept_id})
    concepts = load_concepts()
    for c in concepts:
        if c["id"] == concept_id:
            for k, v in update.model_dump(exclude_none=True).items():
                c[k] = v
            save_concepts(concepts)
            return c
    raise HTTPException(404, "Concept not found")

@app.delete("/api/concepts/{concept_id}")
def delete_concept(concept_id: str):
    _record_history("delete_concept", {"concept_id": concept_id})
    concepts = load_concepts()
    concepts = [c for c in concepts if c["id"] != concept_id]
    save_concepts(concepts)
    return {"ok": True}

@app.post("/api/concepts/from-url")
async def import_concept_from_url(req: URLImport):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
    }
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as http_client:
        try:
            resp = await http_client.get(req.url, headers=headers)
            resp.raise_for_status()
            html = resp.text
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                raise HTTPException(400, f"无法访问该链接（网站拒绝访问，可能是反爬虫机制）。建议：1) 手动添加元概念；2) 尝试其他来源链接；3) 检查链接是否需要登录。错误详情: {e}")
            raise HTTPException(400, f"无法访问该链接: HTTP {e.response.status_code}")
        except Exception as e:
            raise HTTPException(400, f"无法访问该链接: {e}")
    soup = BeautifulSoup(html, "html.parser")
    best_image_url = await _fetch_best_image(soup, req.url)
    local_image = await _download_image(best_image_url)
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)[:6000]
    extra = f"\n用户备注: {req.extra_notes}" if req.extra_notes else ""
    prompt = f"""请从以下网页内容中提取一个设计概念或理论概念。概念可以是建筑理念、空间策略、设计方法、材料应用等任何与设计相关的抽象概念。
请严格按照JSON格式返回：

{{
  "name": "概念名称（简洁，2-8个字）",
  "keywords": ["关键词1", "关键词2", "关键词3", "关键词4", "关键词5"],
  "description": "用2-4句话描述这个概念的核心内容、应用场景和意义"
}}

keywords要求：提取5-8个关键词，涵盖概念的核心特征、相关手法、应用领域等。
description要求：要具体，说明这个概念是什么、如何应用、有什么价值。
{extra}

网页内容：
{text}"""
    try:
        completion = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "你是一个设计理论专家，擅长从文本中提取和归纳设计概念。请只返回JSON，不要添加任何其他文字或markdown格式。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )
        raw = completion.choices[0].message.content.strip()
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
        info = json.loads(raw)
    except Exception as e:
        raise HTTPException(500, f"AI 提取失败: {e}")
    concepts = load_concepts()
    new_concept = {
        "id": f"concept_{uuid.uuid4().hex[:8]}",
        "name": info.get("name", "未命名概念"),
        "keywords": info.get("keywords", []),
        "description": info.get("description", ""),
        "image_url": local_image,
        "source_url": req.url,
    }
    concepts.append(new_concept)
    save_concepts(concepts)
    return new_concept

# —— Nebula Management ——
@app.get("/api/nebulas")
def list_nebulas():
    return load_nebulas()

@app.post("/api/nebulas")
def create_nebula(nebula: NebulaCreate):
    nebulas = load_nebulas()
    cases = load_cases()
    concepts = load_concepts()
    # 验证案例和概念ID是否存在
    for cid in nebula.case_ids:
        if not any(c["id"] == cid for c in cases):
            raise HTTPException(404, f"案例 '{cid}' 不存在")
    for cid in nebula.concept_ids:
        if not any(c["id"] == cid for c in concepts):
            raise HTTPException(404, f"概念 '{cid}' 不存在")
    new_nebula = {"id": f"nebula_{uuid.uuid4().hex[:8]}", "name": nebula.name, "case_ids": nebula.case_ids, "concept_ids": nebula.concept_ids}
    nebulas.append(new_nebula)
    save_nebulas(nebulas)
    return new_nebula

@app.put("/api/nebulas/{nebula_id}")
def update_nebula(nebula_id: str, update: NebulaUpdate):
    nebulas = load_nebulas()
    cases = load_cases()
    concepts = load_concepts()
    for n in nebulas:
        if n["id"] == nebula_id:
            if update.name is not None:
                n["name"] = update.name
            if update.case_ids is not None:
                for cid in update.case_ids:
                    if not any(c["id"] == cid for c in cases):
                        raise HTTPException(404, f"案例 '{cid}' 不存在")
                n["case_ids"] = update.case_ids
            if update.concept_ids is not None:
                for cid in update.concept_ids:
                    if not any(c["id"] == cid for c in concepts):
                        raise HTTPException(404, f"概念 '{cid}' 不存在")
                n["concept_ids"] = update.concept_ids
            save_nebulas(nebulas)
            return n
    raise HTTPException(404, "Nebula not found")

@app.delete("/api/nebulas/{nebula_id}")
def delete_nebula(nebula_id: str):
    nebulas = load_nebulas()
    nebulas = [n for n in nebulas if n["id"] != nebula_id]
    save_nebulas(nebulas)
    return {"ok": True}

# —— AI Inspiration Search（支持豆包/火山方舟联网搜索）——
def _is_volcengine_llm() -> bool:
    base = os.getenv("LLM_BASE_URL", "")
    return "volces.com" in base or "volcengine" in base.lower()


@app.post("/api/search")
def ai_search(req: InspirationQuery):
    cases = load_cases()
    case_summaries = []
    for c in cases:
        tags_str = ", ".join(c.get("tags", []))
        case_summaries.append(
            f"- {c['name']}（{c.get('architect', '未知')}，{c.get('location', '')}）: {tags_str}。{c.get('description', '')}"
        )
    kb = "\n".join(case_summaries)
    tag_hint = ""
    if req.selected_tags:
        tag_hint = f"\n用户当前选中的标签筛选: {', '.join(req.selected_tags)}"

    prompt = f"""你是一个建筑设计灵感顾问。以下是用户的建筑案例知识图谱：

{kb}

用户的设计需求/灵感查询：{req.query}{tag_hint}

请完成以下任务，严格按JSON格式返回：

1. **matched_cases**：从知识图谱中找出与用户需求相关的案例，并说明关联原因
2. **new_suggestions**：推荐3-5个真实存在的建筑案例（知名建筑、建成项目、事务所作品），这些案例应该：
   - 是真实存在的、已建成的建筑项目
   - 与用户需求高度相关
   - 每个案例必须包含 source_url（该案例的网页来源URL，如 ArchDaily、谷德、gooood 等建筑网站的链接）
   - source_url 应该是真实可访问的建筑案例网页链接
3. **design_insights**：基于用户需求和推荐案例，生成3-5条具体可操作的设计策略建议
4. **extended_tags**：推荐3-5个可继续深挖的概念方向

严格按以下JSON格式返回：

{{
  "matched_cases": [
    {{"name": "知识图谱中匹配的案例名称", "reason": "为什么这个案例与需求相关"}}
  ],
  "new_suggestions": [
    {{"name": "推荐案例名称（须为真实存在的建筑项目）", "architect": "建筑师/事务所", "year": "年份", "location": "地点", "tags": ["标签1","标签2"], "description": "2-3句话描述", "reason": "与用户需求的关联", "source_url": "该案例的网页来源URL（必填，如 https://www.archdaily.com/... 或 https://www.gooood.cn/... 等真实建筑网站链接）"}}
  ],
  "design_insights": ["设计策略建议1", "设计策略建议2", "设计策略建议3"],
  "extended_tags": ["可继续探索的概念1", "概念2", "概念3"]
}}

**重要**：
- new_suggestions 中的每个案例必须是真实存在的建筑项目
- source_url 必须是真实可访问的建筑网站链接（ArchDaily、谷德、gooood、Dezeen 等）
- 如果不知道某个案例的具体URL，可以构造合理的URL格式，但优先使用你知识库中的真实案例和URL"""

    try:
        kwargs = {
            "model": LLM_MODEL,
            "messages": [
                {"role": "system", "content": "你是资深建筑评论家和设计顾问。回答要具体、有洞察力。请只返回JSON。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
        }
        # 使用提示词模拟联网搜索：通过详细的提示词引导模型返回带source_url的真实案例
        # 不依赖控制台配置或API工具调用，更稳定可靠
        completion = client.chat.completions.create(**kwargs)
        msg = completion.choices[0].message
        raw = (msg.content or "").strip()
        if not raw and getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls or []:
                if getattr(tc, "function", None) and getattr(tc.function, "arguments", None):
                    raw = tc.function.arguments
                    break
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
        if not raw:
            raise ValueError("模型未返回有效内容")
        result = json.loads(raw)
        if result.get("new_suggestions"):
            for s in result["new_suggestions"]:
                if not s.get("source_url"):
                    s["source_url"] = ""
    except json.JSONDecodeError as e:
        raise HTTPException(500, f"AI 返回格式解析失败: {e}")
    except Exception as e:
        raise HTTPException(500, f"AI 搜索失败: {e}")
    return result

# —— Hybridize ——
DIMENSION_PROMPTS = {
    "手法": "设计手法与空间操作方式（如：减法策略、嵌套、折叠、穿插、架空、悬挑等）",
    "场地处理": "对场地条件的回应方式（如：顺应地形、对抗环境、消隐于自然、重塑场地等）",
    "概念": "设计的核心理念与出发点（如：模糊边界、事件驱动、时间性、身体感知等）",
    "技术": "建造技术与材料策略（如：参数化表皮、预制装配、在地材料、低技策略等）",
    "形式": "建筑形式语言与造型逻辑（如：几何原型、有机形态、解构、极简体量等）",
    "结构": "结构体系与空间的关系（如：结构即空间、大跨度、网壳、悬索、混合结构等）",
}

@app.post("/api/hybridize")
async def hybridize_cases(req: HybridizeRequest):
    cases = load_cases()
    selected = [c for c in cases if c["id"] in req.case_ids]
    if len(selected) < 2:
        raise HTTPException(400, "请至少选择2个案例")
    if not req.dimensions:
        raise HTTPException(400, "请至少选择1个杂交维度")
    
    # 构建每个案例及其对应的维度
    case_blocks = []
    for i, c in enumerate(selected, 1):
        tags_str = ", ".join(c.get("tags", []))
        # 获取该案例对应的维度
        case_dims = []
        if req.case_dimensions and c["id"] in req.case_dimensions:
            case_dims = req.case_dimensions[c["id"]]
        elif req.dimensions:
            # 如果没有指定每个案例的维度，使用所有维度
            case_dims = req.dimensions
        
        dims_desc = ", ".join(case_dims) if case_dims else "未指定"
        case_blocks.append(
            f"【案例{i}】{c['name']}（{c.get('architect','未知')}，{c.get('location','')} {c.get('year','')}）\n"
            f"标签: {tags_str}\n"
            f"描述: {c.get('description','无')}\n"
            f"提取维度: {dims_desc}"
        )
    cases_text = "\n\n".join(case_blocks)
    
    # 构建维度说明（包含自定义维度）
    dim_details = []
    for d in req.dimensions:
        if d in DIMENSION_PROMPTS:
            dim_details.append(f"- {d}: {DIMENSION_PROMPTS[d]}")
        else:
            dim_details.append(f"- {d}: （自定义维度）")
    dims_text = "\n".join(dim_details)

    prompt = f"""你是一个极具创造力的建筑设计顾问。用户选择了以下建筑案例，希望从中提取特定维度进行"设计嫁接"。

选中的案例（每个案例后标注了要提取的维度）：
{cases_text}

所有杂交维度说明：
{dims_text}

要求：
- extraction部分：为每个案例提取其对应的维度（只提取该案例标注的维度）
- 如果某个案例有多个维度，分别提取每个维度的精华
- hybrid_concept部分：将所有案例的提取结果进行创造性重组
- image_prompt部分：生成一个详细的建筑效果图描述，用于AI图像生成

严格按JSON格式返回：
{{
  "extraction": [{{"case_name":"案例名称","dimensions":{{"维度名":"精华提取"}}}}],
  "hybrid_concept": {{
    "title":"概念名称","narrative":"3-5句核心构想",
    "how_it_works":"组合逻辑","possible_scenario":"落地场景","tension_and_potential":"张力与潜力"
  }},
  "image_prompt": "详细的建筑效果图描述，包括建筑外观、材质、环境、光线、视角等，用英文描述，适合AI图像生成"
}}"""

    try:
        completion = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "你是极具创造力的建筑设计顾问。请只返回JSON。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.85,
        )
        raw = completion.choices[0].message.content.strip()
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
        result = json.loads(raw)
        
        # 如果返回了图像提示词，尝试生成效果图（如果启用）
        if result.get("image_prompt") and ENABLE_IMAGE_GENERATION:
            try:
                image_url = await generate_architecture_image(result["image_prompt"])
                result["image_url"] = image_url
            except Exception as img_e:
                # 图像生成失败不影响主要结果
                error_msg = str(img_e)
                # 如果是API不支持的情况，提供更友好的提示
                if "不支持图像生成" in error_msg or "not found" in error_msg.lower() or "404" in error_msg:
                    result["image_error"] = "当前API不支持图像生成功能。如需生成效果图，请使用OpenAI官方API（需支持DALL-E）或设置ENABLE_IMAGE_GENERATION=false禁用此功能。"
                else:
                    result["image_error"] = error_msg
        elif result.get("image_prompt") and not ENABLE_IMAGE_GENERATION:
            result["image_error"] = "图像生成功能已禁用。如需启用，请在.env中设置ENABLE_IMAGE_GENERATION=true并使用支持DALL-E的API。"
    except Exception as e:
        raise HTTPException(500, f"AI 嫁接失败: {e}")
    return result


async def generate_architecture_image(prompt: str) -> str:
    """生成建筑效果图，支持OpenAI DALL-E和豆包API"""
    enhanced_prompt = f"Architectural rendering, professional architectural visualization, {prompt}, high quality, detailed, realistic, architectural photography style"
    
    # 根据配置选择图像生成提供商
    if IMAGE_GENERATION_PROVIDER == "doubao":
        return await generate_doubao_image(enhanced_prompt)
    else:
        return await generate_openai_image(enhanced_prompt)


async def generate_openai_image(prompt: str) -> str:
    """使用OpenAI DALL-E生成图像"""
    try:
        # 尝试使用DALL-E 3
        try:
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            image_url = response.data[0].url
            return image_url
        except Exception as e1:
            # 如果DALL-E 3不可用，尝试DALL-E 2
            try:
                response = client.images.generate(
                    model="dall-e-2",
                    prompt=prompt,
                    size="1024x1024",
                    n=1,
                )
                image_url = response.data[0].url
                return image_url
            except Exception as e2:
                error_msg = str(e1)
                if "dall-e" in error_msg.lower() or "not found" in error_msg.lower() or "404" in error_msg:
                    raise Exception("当前API不支持图像生成功能。请使用OpenAI官方API、豆包API或设置IMAGE_GENERATION_PROVIDER=doubao。")
                raise Exception(f"图像生成失败: {e1}")
    except Exception as e:
        raise Exception(f"OpenAI图像生成失败: {e}")


async def generate_doubao_image(prompt: str) -> str:
    """使用豆包API生成图像"""
    if not DOUBAO_IMAGE_API_KEY:
        raise Exception("未配置豆包图像生成API Key，请在.env中设置DOUBAO_IMAGE_API_KEY")
    
    try:
        async with httpx.AsyncClient(timeout=60) as http:
            headers = {
                "Authorization": f"Bearer {DOUBAO_IMAGE_API_KEY}",
                "Content-Type": "application/json; charset=utf-8"
            }
            payload = {
                "model": "doubao-seedream-4-5-251128",  # 豆包图像模型ID，需要替换为实际值
                "prompt": prompt,
                "size": "2560x1440",
                "n": 1,
                "response_format": "url"
            }
            
            # 确保使用UTF-8编码发送JSON
            response = await http.post(
                DOUBAO_IMAGE_API_URL, 
                json=payload, 
                headers=headers,
                content=None  # 让httpx自动处理编码
            )
            response.raise_for_status()
            result = response.json()
            
            # 豆包API返回格式可能不同，需要根据实际返回调整
            if "data" in result and len(result["data"]) > 0:
                if "url" in result["data"][0]:
                    return result["data"][0]["url"]
                elif "b64_json" in result["data"][0]:
                    # 如果是base64编码，需要保存为文件
                    import base64
                    b64_data = result["data"][0]["b64_json"]
                    image_data = base64.b64decode(b64_data)
                    fname = f"doubao_{uuid.uuid4().hex[:12]}.png"
                    fpath = UPLOAD_DIR / fname
                    fpath.write_bytes(image_data)
                    return f"/static/uploads/{fname}"
            
            raise Exception(f"豆包API返回格式异常: {result}")
    except httpx.HTTPStatusError as e:
        error_detail = ""
        try:
            error_detail = str(e.response.json())
        except:
            try:
                error_detail = e.response.text
            except:
                error_detail = f"HTTP {e.response.status_code}"
        raise Exception(f"豆包API请求失败: HTTP {e.response.status_code} - {error_detail}")
    except Exception as e:
        error_msg = str(e)
        # 确保错误消息可以正确编码
        try:
            error_msg.encode('utf-8')
        except UnicodeEncodeError:
            error_msg = repr(e)
        raise Exception(f"豆包图像生成失败: {error_msg}")

# —— Tag Management ——
@app.get("/api/tags")
def list_tags():
    return load_tags()


@app.post("/api/tags/sync-from-cases")
def sync_tags_from_cases():
    """将当前所有案例中的标签名同步到 tags.json，使标签管理与案例标签统一为一套体系。可多次调用。"""
    cases = load_cases()
    for c in cases:
        sync_case_tags_to_registry(c)
    return {"ok": True, "message": "已将所有案例中的标签同步到标签库"}

@app.post("/api/tags")
def create_tag(tag: TagCreate):
    _record_history("create_tag", {"tag_name": tag.name})
    tags = load_tags()
    cases = load_cases()
    tag_id = f"tag_{uuid.uuid4().hex[:8]}"
    all_parent_ids = tag.parent_ids if tag.parent_ids else ([tag.parent_id] if tag.parent_id else [])
    parent_details = []
    for pid in all_parent_ids:
        is_case = any(c["id"] == pid for c in cases)
        is_tag = pid in tags
        if not is_case and not is_tag:
            raise HTTPException(404, f"父节点 '{pid}' 不存在")
        parent_details.append({"id": pid, "type": "case" if is_case else "tag"})
    for pd in parent_details:
        if pd["type"] == "tag" and pd["id"] in tags:
            if "children" not in tags[pd["id"]]: tags[pd["id"]]["children"] = []
            if tag_id not in tags[pd["id"]]["children"]: tags[pd["id"]]["children"].append(tag_id)
    tags[tag_id] = {"id": tag_id, "name": tag.name, "parent_id": all_parent_ids[0] if len(all_parent_ids)==1 else None, "parent_ids": all_parent_ids, "parent_details": parent_details, "children": []}
    save_tags(tags)
    return tags[tag_id]

@app.put("/api/tags/{tag_id}")
def update_tag(tag_id: str, update: TagUpdate):
    _record_history("update_tag", {"tag_id": tag_id})
    tags = load_tags()
    cases = load_cases()
    if tag_id not in tags: raise HTTPException(404, "Tag not found")
    if update.name is not None: tags[tag_id]["name"] = update.name
    new_parent_ids = None
    if update.parent_ids is not None: new_parent_ids = update.parent_ids
    elif update.parent_id is not None: new_parent_ids = [update.parent_id] if update.parent_id else []
    if new_parent_ids is not None:
        old_pids = tags[tag_id].get("parent_ids", [])
        if not old_pids and tags[tag_id].get("parent_id"): old_pids = [tags[tag_id]["parent_id"]]
        for op in old_pids:
            if op in tags and "children" in tags[op]: tags[op]["children"] = [c for c in tags[op]["children"] if c != tag_id]
        parent_details = []
        for pid in new_parent_ids:
            if pid:
                is_case = any(c["id"]==pid for c in cases)
                is_tag = pid in tags
                if not is_case and not is_tag: raise HTTPException(404, f"父节点 '{pid}' 不存在")
                parent_details.append({"id":pid,"type":"case" if is_case else "tag"})
                if is_tag:
                    if "children" not in tags[pid]: tags[pid]["children"] = []
                    if tag_id not in tags[pid]["children"]: tags[pid]["children"].append(tag_id)
        tags[tag_id]["parent_id"] = new_parent_ids[0] if len(new_parent_ids)==1 else None
        tags[tag_id]["parent_ids"] = new_parent_ids
        tags[tag_id]["parent_details"] = parent_details
    save_tags(tags)
    return tags[tag_id]

@app.delete("/api/tags/{tag_id}")
def delete_tag(tag_id: str):
    _record_history("delete_tag", {"tag_id": tag_id})
    tags = load_tags()
    cases = load_cases()
    if tag_id not in tags: raise HTTPException(404, "Tag not found")
    if tags[tag_id].get("children"): raise HTTPException(400, "请先删除所有子标签")
    pids = tags[tag_id].get("parent_ids", [])
    if not pids and tags[tag_id].get("parent_id"): pids = [tags[tag_id]["parent_id"]]
    for pid in pids:
        if pid in tags and "children" in tags[pid]: tags[pid]["children"] = [c for c in tags[pid]["children"] if c != tag_id]
    tag_name = tags[tag_id]["name"]
    used = [c for c in cases if tag_name in c.get("tags", [])]
    if used: raise HTTPException(400, f"标签 '{tag_name}' 正在被 {len(used)} 个案例使用")
    del tags[tag_id]
    save_tags(tags)
    return {"ok": True}

# —— Graph Data ——
@app.get("/api/graph")
def get_graph(active_nebula_id: str | None = None):
    """获取图谱数据。如果指定 active_nebula_id，则只显示该星云内的节点，其他星云收起显示。"""
    cached = _get_cached_graph(active_nebula_id)
    if cached:
        return cached
    cases = load_cases()
    tags = load_tags()
    concepts = load_concepts()
    nebulas = load_nebulas()
    nodes, edges, tag_set = [], [], set()
    for tid, td in tags.items(): tag_set.add(td["name"])
    
    # 确定要显示的案例和概念ID集合
    visible_case_ids = set()
    visible_concept_ids = set()
    if active_nebula_id:
        active_nebula = next((n for n in nebulas if n["id"] == active_nebula_id), None)
        if active_nebula:
            visible_case_ids = set(active_nebula.get("case_ids", []))
            visible_concept_ids = set(active_nebula.get("concept_ids", []))
        # 如果星云不存在或为空，仍然显示星云节点本身（让用户知道星云是空的）
    
    # 添加案例节点
    for c in cases:
        if not active_nebula_id or c["id"] in visible_case_ids:
            nodes.append({"id":c["id"],"label":c["name"],"type":"case","architect":c.get("architect",""),"description":c.get("description",""),"tags":c.get("tags",[])})
            for tag in c.get("tags",[]):
                tag_id = None
                if tag.startswith("tag_"): tag_id = tag
                else:
                    for tid,td in tags.items():
                        if td["name"]==tag: tag_id=tid; break
                if tag_id and tag_id in tags: edges.append({"source":c["id"],"target":tag_id,"type":"case_tag"})
                else:
                    tag_id = f"tag_{tag}"; tag_set.add(tag)
                    edges.append({"source":c["id"],"target":tag_id,"type":"case_tag"})
    
    # 添加概念节点
    for concept in concepts:
        if not active_nebula_id or concept["id"] in visible_concept_ids:
            nodes.append({"id":concept["id"],"label":concept["name"],"type":"concept","keywords":concept.get("keywords",[]),"description":concept.get("description",""),"image_url":concept.get("image_url",""),"source_url":concept.get("source_url","")})
    
    # 添加标签节点（只添加与可见案例/概念关联的标签）
    if active_nebula_id:
        # 激活星云时，只添加与星云内案例/概念关联的标签
        related_tag_ids = set()
        # 从可见案例的标签中收集标签ID
        for c in cases:
            if c["id"] in visible_case_ids:
                for tag in c.get("tags", []):
                    if tag.startswith("tag_"):
                        related_tag_ids.add(tag)
                    else:
                        for tid, td in tags.items():
                            if td["name"] == tag:
                                related_tag_ids.add(tid)
                                break
        # 添加相关标签节点
        for tid in related_tag_ids:
            if tid in tags:
                td = tags[tid]
                pids = td.get("parent_ids", [])
                pdetails = td.get("parent_details", [])
                if not pids and td.get("parent_id"):
                    pids = [td["parent_id"]]
                    pdetails = [{"id": td["parent_id"], "type": td.get("parent_type", "tag")}]
                is_sub = len(pids) > 0
                is_br = len(pids) > 1
                nodes.append({"id": tid, "label": td["name"], "type": "tag", "parent_ids": pids, "parent_details": pdetails, "is_subtag": is_sub, "is_bridge": is_br})
                for pd in pdetails:
                    # 只添加父节点也在可见范围内的边
                    if pd["type"] == "case":
                        if pd["id"] in visible_case_ids:
                            edges.append({"source": pd["id"], "target": tid, "type": "case_subtag"})
                    else:
                        edges.append({"source": pd["id"], "target": tid, "type": "tag_hierarchy"})
    else:
        # 未激活星云时，添加所有标签节点
        for tid, td in tags.items():
            pids = td.get("parent_ids", [])
            pdetails = td.get("parent_details", [])
            if not pids and td.get("parent_id"):
                pids = [td["parent_id"]]
                pdetails = [{"id": td["parent_id"], "type": td.get("parent_type", "tag")}]
            is_sub = len(pids) > 0
            is_br = len(pids) > 1
            nodes.append({"id": tid, "label": td["name"], "type": "tag", "parent_ids": pids, "parent_details": pdetails, "is_subtag": is_sub, "is_bridge": is_br})
            for pd in pdetails:
                edges.append({"source": pd["id"], "target": tid, "type": "tag_hierarchy" if pd["type"] == "tag" else "case_subtag"})
    
    # 兼容未同步的旧数据：案例中出现的标签名若尚未在 tags 中，仍为其生成节点
    # 只在未激活星云或标签关联到可见案例时添加
    for tag in tag_set:
        tid = f"tag_{tag}"
        if not any(td["name"] == tag for td in tags.values()):
            # 检查这个标签是否关联到可见案例
            should_add = not active_nebula_id
            if active_nebula_id:
                for c in cases:
                    if c["id"] in visible_case_ids and tag in c.get("tags", []):
                        should_add = True
                        break
            if should_add:
                nodes.append({"id": tid, "label": tag, "type": "tag", "parent_ids": [], "parent_details": [], "is_subtag": False, "is_bridge": False})
    
    # 添加星云节点
    for nebula in nebulas:
        is_active = nebula["id"] == active_nebula_id
        nodes.append({
            "id": nebula["id"],
            "label": nebula["name"],
            "type": "nebula",
            "case_ids": nebula.get("case_ids", []),
            "concept_ids": nebula.get("concept_ids", []),
            "is_active": is_active,
            "is_collapsed": not is_active and active_nebula_id is not None
        })
        # 星云到其包含的案例/概念的边
        for cid in nebula.get("case_ids", []):
            if not active_nebula_id or is_active:
                edges.append({"source": nebula["id"], "target": cid, "type": "nebula_case"})
        for cid in nebula.get("concept_ids", []):
            if not active_nebula_id or is_active:
                edges.append({"source": nebula["id"], "target": cid, "type": "nebula_concept"})
    
    # 计算星云之间的连接（基于共享案例数）
    for i, n1 in enumerate(nebulas):
        for n2 in nebulas[i+1:]:
            shared_cases = set(n1.get("case_ids", [])) & set(n2.get("case_ids", []))
            shared_concepts = set(n1.get("concept_ids", [])) & set(n2.get("concept_ids", []))
            shared_count = len(shared_cases) + len(shared_concepts)
            if shared_count > 0:
                # 共享数量越多，权重越大（用于前端决定线的粗细/亮度）
                edges.append({
                    "source": n1["id"],
                    "target": n2["id"],
                    "type": "nebula_link",
                    "weight": shared_count,
                    "shared_cases": list(shared_cases),
                    "shared_concepts": list(shared_concepts)
                })
    
    result = {"nodes": nodes, "edges": edges}
    _set_cached_graph(active_nebula_id, result)
    return result

@app.post("/api/cases/from-suggestion")
def add_from_suggestion(case: CaseCreate):
    cases = load_cases()
    for c in cases:
        if c["name"]==case.name: raise HTTPException(409, f"'{case.name}' 已存在")
    new_case = {"id":f"case_{uuid.uuid4().hex[:8]}", **case.model_dump()}
    cases.append(new_case)
    save_cases(cases)
    sync_case_tags_to_registry(new_case)
    return new_case

# —— Data Export/Import ——
@app.get("/api/export/json")
def export_json():
    """导出完整数据为JSON格式"""
    data = {
        "cases": load_cases(),
        "concepts": load_concepts(),
        "tags": load_tags(),
        "nebulas": load_nebulas(),
        "export_time": str(uuid.uuid4()),  # 简单的时间戳
        "version": "1.0"
    }
    return Response(
        content=json.dumps(data, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=archgraph_export.json"}
    )

@app.get("/api/export/csv")
def export_csv():
    """导出案例数据为CSV格式"""
    cases = load_cases()
    import csv
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "名称", "建筑师", "年份", "地点", "标签", "描述", "图片URL", "来源URL"])
    for c in cases:
        writer.writerow([
            c.get("id", ""),
            c.get("name", ""),
            c.get("architect", ""),
            c.get("year", ""),
            c.get("location", ""),
            ", ".join(c.get("tags", [])),
            c.get("description", "").replace("\n", " "),
            c.get("image_url", ""),
            c.get("source_url", "")
        ])
    return Response(
        content=output.getvalue().encode("utf-8-sig"),  # BOM for Excel
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=archgraph_cases.csv"}
    )

@app.get("/api/export/graphml")
def export_graphml():
    """导出图谱数据为GraphML格式（可用于Gephi等工具）"""
    graph_data = get_graph()
    graphml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    graphml += '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">\n'
    graphml += '  <key id="type" for="node" attr.name="type" attr.type="string"/>\n'
    graphml += '  <key id="label" for="node" attr.name="label" attr.type="string"/>\n'
    graphml += '  <key id="weight" for="edge" attr.name="weight" attr.type="double"/>\n'
    graphml += '  <graph id="G" edgedefault="directed">\n'
    for node in graph_data["nodes"]:
        graphml += f'    <node id="{node["id"]}">\n'
        graphml += f'      <data key="type">{node.get("type", "unknown")}</data>\n'
        graphml += f'      <data key="label">{node.get("label", "")}</data>\n'
        graphml += '    </node>\n'
    for edge in graph_data["edges"]:
        source = edge["source"] if isinstance(edge["source"], str) else edge["source"]["id"]
        target = edge["target"] if isinstance(edge["target"], str) else edge["target"]["id"]
        weight = edge.get("weight", 1.0)
        graphml += f'    <edge source="{source}" target="{target}">\n'
        graphml += f'      <data key="weight">{weight}</data>\n'
        graphml += '    </edge>\n'
    graphml += '  </graph>\n'
    graphml += '</graphml>'
    return Response(
        content=graphml.encode("utf-8"),
        media_type="application/xml",
        headers={"Content-Disposition": "attachment; filename=archgraph.graphml"}
    )

class ImportData(BaseModel):
    cases: Optional[list[dict]] = None
    concepts: Optional[list[dict]] = None
    tags: Optional[dict] = None
    nebulas: Optional[list[dict]] = None
    merge_mode: str = "append"  # "append" 或 "replace"

@app.post("/api/import/json")
def import_json(data: ImportData):
    """从JSON导入数据"""
    _record_history("import", {"merge_mode": data.merge_mode})
    if data.merge_mode == "replace":
        if data.cases is not None:
            save_cases(data.cases)
        if data.concepts is not None:
            save_concepts(data.concepts)
        if data.tags is not None:
            save_tags(data.tags)
        if data.nebulas is not None:
            save_nebulas(data.nebulas)
    else:  # append
        if data.cases:
            existing = load_cases()
            existing_ids = {c["id"] for c in existing}
            new_cases = [c for c in data.cases if c.get("id") not in existing_ids]
            existing.extend(new_cases)
            save_cases(existing)
        if data.concepts:
            existing = load_concepts()
            existing_ids = {c["id"] for c in existing}
            new_concepts = [c for c in data.concepts if c.get("id") not in existing_ids]
            existing.extend(new_concepts)
            save_concepts(existing)
        if data.tags:
            existing = load_tags()
            existing.update(data.tags)
            save_tags(existing)
        if data.nebulas:
            existing = load_nebulas()
            existing_ids = {n["id"] for n in existing}
            new_nebulas = [n for n in data.nebulas if n.get("id") not in existing_ids]
            existing.extend(new_nebulas)
            save_nebulas(existing)
    return {"ok": True, "message": "导入成功"}

# —— Version History & Snapshots ——
def _load_history():
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"actions": [], "undo_stack": [], "redo_stack": []}

def _save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def _record_history(action_type: str, data: dict):
    """记录操作历史"""
    history = _load_history()
    snapshot = {
        "cases": load_cases(),
        "concepts": load_concepts(),
        "tags": load_tags(),
        "nebulas": load_nebulas()
    }
    history["actions"].append({
        "type": action_type,
        "data": data,
        "timestamp": str(uuid.uuid4()),
        "snapshot": snapshot
    })
    history["undo_stack"].append(snapshot)
    history["redo_stack"] = []  # 清空重做栈
    if len(history["actions"]) > 100:  # 限制历史记录数量
        history["actions"] = history["actions"][-100:]
    if len(history["undo_stack"]) > 50:  # 限制撤销栈大小
        history["undo_stack"] = history["undo_stack"][-50:]
    _save_history(history)

@app.post("/api/history/undo")
def undo():
    """撤销操作"""
    history = _load_history()
    if not history["undo_stack"]:
        raise HTTPException(400, "没有可撤销的操作")
    current_snapshot = {
        "cases": load_cases(),
        "concepts": load_concepts(),
        "tags": load_tags(),
        "nebulas": load_nebulas()
    }
    history["redo_stack"].append(current_snapshot)
    prev_snapshot = history["undo_stack"].pop()
    save_cases(prev_snapshot["cases"])
    save_concepts(prev_snapshot["concepts"])
    save_tags(prev_snapshot["tags"])
    save_nebulas(prev_snapshot["nebulas"])
    _save_history(history)
    return {"ok": True}

@app.post("/api/history/redo")
def redo():
    """重做操作"""
    history = _load_history()
    if not history["redo_stack"]:
        raise HTTPException(400, "没有可重做的操作")
    current_snapshot = {
        "cases": load_cases(),
        "concepts": load_concepts(),
        "tags": load_tags(),
        "nebulas": load_nebulas()
    }
    history["undo_stack"].append(current_snapshot)
    next_snapshot = history["redo_stack"].pop()
    save_cases(next_snapshot["cases"])
    save_concepts(next_snapshot["concepts"])
    save_tags(next_snapshot["tags"])
    save_nebulas(next_snapshot["nebulas"])
    _save_history(history)
    return {"ok": True}

class SnapshotCreate(BaseModel):
    name: Optional[str] = None

@app.post("/api/snapshots")
def create_snapshot(data: SnapshotCreate):
    """创建快照"""
    snapshot_id = f"snapshot_{uuid.uuid4().hex[:8]}"
    snapshot_name = data.name or f"快照_{snapshot_id[-6:]}"
    snapshot_data = {
        "id": snapshot_id,
        "name": snapshot_name,
        "timestamp": str(uuid.uuid4()),
        "cases": load_cases(),
        "concepts": load_concepts(),
        "tags": load_tags(),
        "nebulas": load_nebulas()
    }
    snapshot_file = SNAPSHOTS_DIR / f"{snapshot_id}.json"
    with open(snapshot_file, "w", encoding="utf-8") as f:
        json.dump(snapshot_data, f, ensure_ascii=False, indent=2)
    return {"ok": True, "snapshot_id": snapshot_id}

@app.get("/api/snapshots")
def list_snapshots():
    """列出所有快照"""
    snapshots = []
    for f in SNAPSHOTS_DIR.glob("snapshot_*.json"):
        try:
            with open(f, "r", encoding="utf-8") as file:
                data = json.load(file)
                snapshots.append({
                    "id": data.get("id"),
                    "name": data.get("name", "未命名快照"),
                    "timestamp": data.get("timestamp", "")
                })
        except:
            continue
    snapshots.sort(key=lambda x: x["timestamp"], reverse=True)
    return {"snapshots": snapshots}

@app.post("/api/snapshots/{snapshot_id}/restore")
def restore_snapshot(snapshot_id: str):
    """恢复快照"""
    snapshot_file = SNAPSHOTS_DIR / f"{snapshot_id}.json"
    if not snapshot_file.exists():
        raise HTTPException(404, "快照不存在")
    with open(snapshot_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    save_cases(data.get("cases", []))
    save_concepts(data.get("concepts", []))
    save_tags(data.get("tags", {}))
    save_nebulas(data.get("nebulas", []))
    return {"ok": True}

@app.delete("/api/snapshots/{snapshot_id}")
def delete_snapshot(snapshot_id: str):
    """删除快照"""
    snapshot_file = SNAPSHOTS_DIR / f"{snapshot_id}.json"
    if snapshot_file.exists():
        snapshot_file.unlink()
    return {"ok": True}

# —— Serve frontend ——
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def index():
    return FileResponse("static/index.html")