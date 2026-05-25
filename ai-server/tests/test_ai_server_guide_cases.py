"""MCP Client 테스트 가이드 AI Server 케이스 수동 검증 스크립트.

사용법:
  cd ai-server
  python tests/test_ai_server_guide_cases.py

주의:
  이 스크립트는 recommend_service()를 직접 호출하므로 uvicorn을 켤 필요가 없습니다.
  TC-AI-05/06은 MCP Client 오류 처리 로그 검증 항목이라 여기서는 제외합니다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.service_recommend import recommend_service

CASES = [
    ("TC-AI-01", "주민등록등본 발급받고 싶어요", "RESIDENT_REGISTRATION_COPY", lambda r: r["confidence"] >= 0.6),
    ("TC-AI-02", "전입신고 하려고요", "MOVE_IN_REPORT", lambda r: r["confidence"] >= 0.6),
    ("TC-AI-03", "어르신 글씨 크게 해주세요", None, lambda r: "어르신" in r.get("answer", "")),
    ("TC-AI-04", "날씨 알려줘", None, lambda r: r["confidence"] < 0.6),
    ("TC-AI-07", "여권 발급해줘", None, lambda r: r["confidence"] >= 0.6 and "현재 제공되지 않는 서비스" in r.get("answer", "")),
]


def main() -> None:
    for case_id, text, expected_service_id, extra_check in CASES:
        result = recommend_service(text)
        ok_service = result.get("serviceId") == expected_service_id
        ok_extra = extra_check(result)
        status = "PASS" if ok_service and ok_extra else "FAIL"
        print("=" * 80)
        print(case_id, status)
        print("input:", text)
        print("intent:", result.get("intent"))
        print("serviceId:", result.get("serviceId"))
        print("confidence:", result.get("confidence"))
        print("answer:", result.get("answer"))
        print("source:", result.get("source"))


if __name__ == "__main__":
    main()
