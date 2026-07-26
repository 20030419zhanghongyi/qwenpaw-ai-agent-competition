"""Run a real HTTP smoke test for the complete Lotus City story workflow."""

from __future__ import annotations

import argparse
import time

import httpx


STORY_ID = "lotus_city_double_map"
PASSWORD = "StoryE2EPassword123!"


def _expect(response: httpx.Response, status_code: int) -> dict:
    if response.status_code != status_code:
        raise RuntimeError(
            f"{response.request.method} {response.request.url.path} "
            f"returned {response.status_code}: {response.text}"
        )
    return response.json()


def run(base_url: str) -> None:
    email = f"story-e2e-{int(time.time() * 1000)}@test.local"
    with httpx.Client(base_url=base_url, timeout=20) as client:
        registered = _expect(
            client.post(
                "/api/v1/users/register",
                json={
                    "email": email,
                    "password": PASSWORD,
                    "name": "故事全链路测试",
                    "language": "zh-CN",
                    "country": "MO",
                },
            ),
            201,
        )
        token = registered["token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"PASS 1. 注册并取得 Token - 用户 {registered['user_id']}")

        current_user = _expect(client.get("/api/v1/users/me", headers=headers), 200)
        if current_user["user"]["email"] != email:
            raise RuntimeError("当前用户与注册用户不一致")
        print("PASS 2. 使用 Token 获取当前用户")

        story = _expect(client.get(f"/api/v1/stories/{STORY_ID}"), 200)
        if story["version"] != 4 or len(story["nodes"]) != 7:
            raise RuntimeError("故事版本或章节数量不符合 V4 冻结规范")
        if "solution" in str(story):
            raise RuntimeError("公开故事接口泄漏了解谜答案")
        print("PASS 3. 获取 V4 故事且公开内容不含答案")

        story_session = _expect(
            client.post(f"/api/v1/stories/{STORY_ID}/sessions", headers=headers),
            201,
        )
        session_id = story_session["session_id"]
        trip_id = story_session["trip_id"]
        print(f"PASS 4. 创建故事会话及配套 Trip - {session_id}")

        for node in sorted(story["nodes"], key=lambda item: item["order"]):
            chapter_id = node["id"]
            if node.get("poi_id"):
                _expect(
                    client.post(
                        f"/api/v1/story-sessions/{session_id}/actions",
                        headers=headers,
                        json={"action": "arrive", "chapter_id": chapter_id},
                    ),
                    200,
                )

            if node["kind"] == "puzzle":
                action = {"action": "skip", "chapter_id": chapter_id}
            elif node["kind"] == "prologue":
                action = {"action": "continue", "chapter_id": chapter_id}
            else:
                action = {
                    "action": "choose_ending",
                    "chapter_id": chapter_id,
                    "choice_id": "complete_today_note",
                    "reflection": "今天的澳门仍在变化，我把所见与来源留给后来的人。",
                }
            result = _expect(
                client.post(
                    f"/api/v1/story-sessions/{session_id}/actions",
                    headers=headers,
                    json=action,
                ),
                200,
            )
            if not result["accepted"]:
                raise RuntimeError(f"章节操作未被接受：{chapter_id}")
        print("PASS 5. 完成序章、六处地点、五次可跳过解谜及最终选择")

        restored = _expect(
            client.get(f"/api/v1/story-sessions/{session_id}", headers=headers),
            200,
        )
        if restored["status"] != "completed":
            raise RuntimeError("故事会话未完成")
        if restored["progress"]["completed_chapters"] != 7:
            raise RuntimeError("故事章节进度不完整")
        if restored["progress"]["skipped_puzzles"] != 5:
            raise RuntimeError("可跳过关卡进度未正确记录")
        print("PASS 6. 恢复故事会话并核对章节、跳关及结局状态")

        trip_progress = _expect(client.get(f"/api/v1/trips/{trip_id}/progress"), 200)
        if (
            trip_progress["completed_stops"] != 6
            or trip_progress["completion_ratio"] != 1
        ):
            raise RuntimeError("故事配套 Trip 未同步完成")
        print("PASS 7. 故事进度与六站 Trip 进度一致")
        print(f"PASS 完整链路：用户 {registered['user_id']}，Trip {trip_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    run(args.base_url.rstrip("/"))
