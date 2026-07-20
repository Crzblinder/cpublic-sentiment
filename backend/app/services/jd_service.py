"""JD 解析服务。"""

from __future__ import annotations

from typing import Any

from app.agents.jd_parser import JDParser


class JDService:
    def parse_jd_text(self, text: str) -> dict[str, Any]:
        parser = JDParser()
        return parser.parse_jd(text)
