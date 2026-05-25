# db/mysql_client.py
# -*- coding: utf-8 -*-

import pymysql
from core.config_manager import load_config


def get_connection():
    cfg = load_config()["database"]

    return pymysql.connect(
        host=cfg.get("host", "127.0.0.1"),
        port=int(cfg.get("port", 3306)),
        user=cfg.get("user", "atg_app"),
        password=cfg.get("password", ""),
        database=cfg.get("database", "atg_order_system"),
        charset=cfg.get("charset", "utf8mb4"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def fetch_all(sql, params=None):
    params = params or []

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def fetch_one(sql, params=None):
    params = params or []

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()


def execute(sql, params=None):
    params = params or []

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount