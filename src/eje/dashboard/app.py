"""Streamlit dashboard for the Moral Ops Center."""
from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from eje.config.settings import Settings, get_settings
from eje.db import escalation_log


@st.cache_resource
def get_engine(settings: Settings):
    engine = escalation_log.get_engine(settings.db_path)
    escalation_log.init_db(engine)
    return engine


def render_header(settings: Settings) -> None:
    st.title("ELEANOR Moral Ops Center")
    st.caption(f"Config: {settings.config_path} | DB: {settings.db_path}")


def render_recent_cases(engine, limit: int = 10) -> None:
    st.subheader("Recent Decisions")
    rows = escalation_log.fetch_recent(engine, limit=limit)
    data = [
        {
            "case_id": row.case_id,
            "verdict": row.verdict,
            "confidence": row.confidence,
            "escalated": row.escalated,
            "created_at": row.created_at,
        }
        for row in rows
    ]
    st.dataframe(pd.DataFrame(data))


def render_top_dissent(engine, limit: int = 10) -> None:
    st.subheader("Top Dissenting Critics")
    dissenters = escalation_log.get_top_dissent(engine, limit=limit)
    if not dissenters:
        st.info("No dissent data yet.")
        return
    st.bar_chart(pd.DataFrame(dissenters).set_index("critic"))


def render_exports(engine) -> None:
    st.subheader("Export Data")
    rows = escalation_log.fetch_recent(engine, limit=100)
    raw_json = [
        {
            "case_id": row.case_id,
            "prompt": row.prompt,
            "verdict": row.verdict,
            "confidence": row.confidence,
            "escalated": row.escalated,
            "precedents": json.loads(row.precedents or "[]"),
            "critic_reports": json.loads(row.critic_reports or "[]"),
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]
    st.download_button(
        "Download last 100 decisions as JSON",
        data=json.dumps(raw_json, indent=2),
        file_name="decisions.json",
        mime="application/json",
    )


def main(settings: Settings | None = None):
    settings = settings or get_settings()
    engine = get_engine(settings)

    render_header(settings)
    render_recent_cases(engine)
    render_top_dissent(engine)
    render_exports(engine)


if __name__ == "__main__":
    main()
