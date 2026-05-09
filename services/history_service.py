"""
history_service.py - 选股历史记录持久化（SQLite）
"""
import json
import os
import sqlite3
import threading
from datetime import datetime
from typing import List, Dict, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "stock_selector.db")

_init_lock = threading.Lock()
_inited = False


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """建表（幂等）。进程生命周期内只跑一次。"""
    global _inited
    with _init_lock:
        if _inited:
            return
        with _conn() as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS selection_snapshot (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    note TEXT,
                    params TEXT,
                    count INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS selection_item (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER NOT NULL,
                    code TEXT NOT NULL,
                    name TEXT,
                    price REAL,
                    total_score REAL,
                    tech_score REAL,
                    fund_score REAL,
                    sentiment_score REAL,
                    pe REAL,
                    pb REAL,
                    current_price REAL,
                    change_pct REAL,
                    price_updated_at TEXT,
                    FOREIGN KEY (snapshot_id) REFERENCES selection_snapshot(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_item_snapshot ON selection_item(snapshot_id);
                """
            )
            # 老表升级：补齐新字段（幂等）
            for col, typ in [
                ("current_price", "REAL"),
                ("change_pct", "REAL"),
                ("price_updated_at", "TEXT"),
            ]:
                try:
                    c.execute(f"ALTER TABLE selection_item ADD COLUMN {col} {typ}")
                except sqlite3.OperationalError:
                    pass  # 列已存在
        _inited = True


def _safe_float(v) -> Optional[float]:
    try:
        if v is None:
            return None
        f = float(v)
        if f != f:  # NaN
            return None
        return f
    except (TypeError, ValueError):
        return None


def save_snapshot(items: List[Dict], params: Dict, note: str = "") -> int:
    """保存一次选股结果，返回 snapshot_id。"""
    if not items:
        raise ValueError("items 为空，无法保存")

    created_at = datetime.now().isoformat(timespec="seconds")
    params_json = json.dumps(params or {}, ensure_ascii=False)

    with _conn() as c:
        cur = c.execute(
            "INSERT INTO selection_snapshot (created_at, note, params, count) VALUES (?, ?, ?, ?)",
            (created_at, note or "", params_json, len(items)),
        )
        sid = cur.lastrowid
        c.executemany(
            """
            INSERT INTO selection_item
                (snapshot_id, code, name, price, total_score, tech_score, fund_score, sentiment_score, pe, pb)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    sid,
                    it.get("code"),
                    it.get("name"),
                    _safe_float(it.get("price")),
                    _safe_float(it.get("total_score")),
                    _safe_float(it.get("tech_score")),
                    _safe_float(it.get("fund_score")),
                    _safe_float(it.get("sentiment_score")),
                    _safe_float(it.get("pe")),
                    _safe_float(it.get("pb")),
                )
                for it in items
            ],
        )
    return sid


def list_snapshots() -> List[Dict]:
    """列出所有快照（按时间倒序），附带平均总分 + 胜率（基于上次查看时缓存的 change_pct）。"""
    with _conn() as c:
        rows = c.execute(
            """
            SELECT s.id, s.created_at, s.note, s.count,
                   (SELECT AVG(total_score) FROM selection_item WHERE snapshot_id=s.id) AS avg_score,
                   (SELECT COUNT(*) FROM selection_item WHERE snapshot_id=s.id AND change_pct IS NOT NULL) AS evaluated_count,
                   (SELECT COUNT(*) FROM selection_item WHERE snapshot_id=s.id AND change_pct > 0) AS win_count,
                   (SELECT AVG(change_pct) FROM selection_item WHERE snapshot_id=s.id AND change_pct IS NOT NULL) AS avg_change_pct,
                   (SELECT MAX(price_updated_at) FROM selection_item WHERE snapshot_id=s.id) AS last_priced_at
            FROM selection_snapshot s
            ORDER BY s.id DESC
            """
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        evaluated = d.get("evaluated_count") or 0
        wins = d.get("win_count") or 0
        d["win_rate"] = round(wins / evaluated * 100, 1) if evaluated > 0 else None
        result.append(d)
    return result


def get_snapshot(sid: int) -> Optional[Dict]:
    """取某快照 meta + 全部 items；不存在返回 None。"""
    with _conn() as c:
        meta = c.execute(
            "SELECT id, created_at, note, params, count FROM selection_snapshot WHERE id=?",
            (sid,),
        ).fetchone()
        if not meta:
            return None
        items = c.execute(
            """
            SELECT id, code, name, price, total_score, tech_score, fund_score, sentiment_score, pe, pb,
                   current_price, change_pct, price_updated_at
            FROM selection_item WHERE snapshot_id=? ORDER BY total_score DESC
            """,
            (sid,),
        ).fetchall()
    snapshot = dict(meta)
    try:
        snapshot["params"] = json.loads(snapshot.get("params") or "{}")
    except Exception:
        snapshot["params"] = {}
    snapshot["items"] = [dict(r) for r in items]
    return snapshot


def update_item_prices(updates: List[Dict]) -> None:
    """
    批量更新 items 的当前价/涨跌幅/更新时间。
    updates: [{"id": 1, "current_price": 12.3, "change_pct": 5.2}, ...]
    """
    if not updates:
        return
    now = datetime.now().isoformat(timespec="seconds")
    with _conn() as c:
        c.executemany(
            """
            UPDATE selection_item
            SET current_price=?, change_pct=?, price_updated_at=?
            WHERE id=?
            """,
            [
                (u.get("current_price"), u.get("change_pct"), now, u["id"])
                for u in updates
            ],
        )


def delete_snapshot(sid: int) -> bool:
    """删除快照（级联删 items）。返回是否真的删了。"""
    with _conn() as c:
        cur = c.execute("DELETE FROM selection_snapshot WHERE id=?", (sid,))
        return cur.rowcount > 0
