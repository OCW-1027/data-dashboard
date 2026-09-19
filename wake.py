# -*- coding: utf-8 -*-
"""
wake.py — Streamlit Community Cloud 절전 해제
=============================================
Streamlit Cloud는 일정 시간 접속이 없으면 앱을 재우고, "Yes, get this app back up!"
버튼을 사람이 눌러야 깨어난다. HTTP 요청(cron-job.org 등)은 서버 껍데기만 200으로
응답할 뿐 앱 프로세스를 깨우지 못한다 — 실제 브라우저가 필요하다.

이 스크립트는 헤드리스 Chromium으로 페이지를 열어
  1) 절전 화면이면 버튼을 누르고
  2) 앱이 뜰 때까지 기다린 뒤
  3) 세션을 잠시 유지한다 (활동으로 기록되도록)

GitHub Actions에서 4시간마다 실행한다 (keepalive.yml).
"""
import sys
import time

from playwright.sync_api import sync_playwright

URL = "https://daiji-data.streamlit.app/"
WAKE_TEXT = "get this app back up"
BOOT_WAIT = 150        # 기동 대기 최대 초
HOLD = 40              # 기동 후 세션 유지 초


def frame_texts(page):
    out = []
    for fr in page.frames:
        try:
            out.append(fr.evaluate("document.body ? document.body.innerText : ''") or "")
        except Exception:
            out.append("")
    return out


def state_of(page):
    texts = " ".join(frame_texts(page))
    if "Zzzz" in texts or WAKE_TEXT in texts:
        return "sleeping"
    if "in the oven" in texts:
        return "booting"
    return "awake"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(URL, timeout=90_000)
        page.wait_for_timeout(8_000)

        st = state_of(page)
        print(f"[1] 초기 상태: {st}")

        if st == "sleeping":
            clicked = False
            for fr in page.frames:
                try:
                    btn = fr.get_by_text(WAKE_TEXT, exact=False)
                    if btn.count():
                        btn.first.click()
                        clicked = True
                        print("[2] 깨우기 버튼 클릭")
                        break
                except Exception:
                    continue
            if not clicked:
                print("[2] 버튼을 찾지 못함")
                browser.close()
                sys.exit(1)

            t0 = time.time()
            while time.time() - t0 < BOOT_WAIT:
                page.wait_for_timeout(10_000)
                st = state_of(page)
                print(f"    {int(time.time() - t0):>3}s  {st}")
                if st == "awake":
                    break
            if st != "awake":
                print(f"[3] {BOOT_WAIT}초 내 기동 확인 실패 — 다음 실행에서 재시도")
                browser.close()
                sys.exit(0)        # 실패로 처리하지 않음 (다음 주기에 다시 시도)

        # 활동으로 기록되도록 세션을 잠시 유지
        page.wait_for_timeout(HOLD * 1000)
        print(f"[4] 세션 {HOLD}초 유지 후 종료 — 최종 상태: {state_of(page)}")
        browser.close()


if __name__ == "__main__":
    main()
