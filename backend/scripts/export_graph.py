"""导出 LangGraph 工作流的 Mermaid 图。

用法:
    cd backend
    py scripts/export_graph.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os
os.environ.setdefault("OPENAI_API_KEY", "")
os.environ.setdefault("DATABASE_URL", "sqlite:///./sentiment.db")
os.environ.setdefault("VECTOR_DB_PATH", "./chroma_data")

from app.models.base import Base, SessionLocal, engine
from app.agents.workflow import build_sentiment_graph


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        graph = build_sentiment_graph(db)

        # Mermaid 输出
        mermaid = graph.get_graph().draw_mermaid()
        print("=== Mermaid Diagram ===")
        print(mermaid)
        print()

        # ASCII 输出
        print("=== ASCII Graph ===")
        print(graph.get_graph().draw_ascii())

        # 保存 Mermaid 到文件
        out_path = Path(__file__).resolve().parent.parent / "docs" / "workflow.mmd"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(mermaid, encoding="utf-8")
        print(f"\nMermaid saved to: {out_path}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
