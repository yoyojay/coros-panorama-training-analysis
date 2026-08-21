#!/usr/bin/env python3
"""
直接调用 COROS Training Hub API 获取指定日期范围数据（脱敏分享版）。
用法：设置环境变量 COROS_EMAIL / COROS_PASSWORD（或直接改下方占位符），
再运行：python3 fetch_data.py 20260801 20260818
"""
import asyncio
import hashlib
import json
import os
import sys
import time
import httpx

# ============ 配置（请替换为你自己的账号，或设置环境变量）============
COROS_EMAIL = os.environ.get("COROS_EMAIL", "YOUR_EMAIL@example.com")
COROS_PASSWORD = os.environ.get("COROS_PASSWORD", "YOUR_PASSWORD")
COROS_REGION = "asia"   # asia/cn | eu | us

BASE_URLS = {
    "asia": "https://teamcnapi.coros.com",
    "cn": "https://teamcnapi.coros.com",
    "eu": "https://teameuapi.coros.com",
    "us": "https://teamapi.coros.com",
}
BASE_URL = BASE_URLS.get(COROS_REGION, BASE_URLS["asia"])
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"

START_DAY = sys.argv[1] if len(sys.argv) > 1 else "20260801"
END_DAY = sys.argv[2] if len(sys.argv) > 2 else "20260818"
OUTPUT_FILE = sys.argv[3] if len(sys.argv) > 3 else f"coros_{START_DAY}_{END_DAY}.json"


class CorosAPI:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60)
        self.token = None
        self.user_id = None

    async def login(self):
        pwd = hashlib.md5(COROS_PASSWORD.encode()).hexdigest()
        resp = await self.client.post(
            f"{BASE_URL}/account/login",
            json={"account": COROS_EMAIL, "accountType": 2, "pwd": pwd},
            headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
        )
        resp.raise_for_status()
        b = resp.json()
        if b.get("result") != "0000":
            raise ValueError(f"Login failed: {b.get('message')}")
        self.token = b["data"]["accessToken"]
        self.user_id = b["data"]["userId"]
        print(f"[OK] 登录成功！User ID: {self.user_id}")

    def _h(self):
        return {
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
            "accessToken": self.token,
            "yfheader": json.dumps({"userId": self.user_id}),
        }

    async def daily_metrics(self, start, end):
        """GET /analyse/dayDetail/query — 每日指标（RHR/HRV/疲劳/负荷）"""
        resp = await self.client.get(
            f"{BASE_URL}/analyse/dayDetail/query",
            params={"startDay": start, "endDay": end},
            headers=self._h(),
        )
        resp.raise_for_status()
        b = resp.json()
        if b.get("result") != "0000":
            raise ValueError(f"daily_metrics: {b.get('message')}")
        return b.get("data", {})

    async def analyse_summary(self):
        """POST /analyse/query — VO2max/负荷平衡(t7dayList: ati/cti) 摘要"""
        resp = await self.client.post(f"{BASE_URL}/analyse/query", json={}, headers=self._h())
        resp.raise_for_status()
        b = resp.json()
        if b.get("result") != "0000":
            return {}
        return b.get("data", {})

    async def activities(self, start, end):
        """GET /activity/query — 活动列表（分页合并）"""
        all_items = []
        page = 1
        while True:
            resp = await self.client.get(
                f"{BASE_URL}/activity/query",
                params={"startDay": start, "endDay": end, "pageNumber": page, "size": 50},
                headers=self._h(),
            )
            resp.raise_for_status()
            b = resp.json()
            if b.get("result") != "0000":
                raise ValueError(f"activities: {b.get('message')}")
            data = b.get("data", {})
            items = data.get("dataList", data.get("list", []))
            all_items.extend(items)
            total = data.get("totalCount", 0)
            if len(all_items) >= total or not items:
                break
            page += 1
        return all_items

    async def activity_detail(self, label_id, sport_type):
        """POST /activity/detail/query —— 必须 form-data(labelId+userId+sportType)+yfheader，JSON body 会返回 1001"""
        resp = await self.client.post(
            f"{BASE_URL}/activity/detail/query",
            data={"labelId": label_id, "userId": self.user_id, "sportType": str(sport_type)},
            headers={"User-Agent": USER_AGENT, "accessToken": self.token,
                     "yfheader": json.dumps({"userId": self.user_id})},
        )
        resp.raise_for_status()
        b = resp.json()
        if b.get("result") != "0000":
            return {}
        return b.get("data", {})

    async def close(self):
        await self.client.aclose()


async def main():
    if "YOUR_" in COROS_EMAIL or "YOUR_" in COROS_PASSWORD:
        print("[WARN] 请先设置 COROS_EMAIL / COROS_PASSWORD 环境变量，或在脚本顶部填入你的账号。")
        return
    api = CorosAPI()
    try:
        await api.login()
        print("[..] 获取每日指标...")
        metrics = await api.daily_metrics(START_DAY, END_DAY)
        print("[..] 获取 analyse 摘要（含 ati/cti 负荷平衡）...")
        analyse = await api.analyse_summary()
        print("[..] 获取活动列表...")
        activities = await api.activities(START_DAY, END_DAY)
        print(f"     共 {len(activities)} 条活动")

        all_data = {
            "metrics": metrics,
            "analyse": analyse,
            "activities": activities,
            "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        print(f"[OK] 数据已保存: {OUTPUT_FILE}")

        run_acts = [a for a in activities if a.get("sportType") in (100, 102, 103)]
        total_dist = sum(a.get("distance", 0) or 0 for a in run_acts) / 1000
        print(f"[..] 跑步 {len(run_acts)} 次 | 总距离 {total_dist:.1f} km")
    finally:
        await api.close()


if __name__ == "__main__":
    asyncio.run(main())
