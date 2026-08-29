from __future__ import annotations

from artha.dossier.render import render_markdown


def test_render_markdown_includes_all_sections_for_track_a(valid_dossier_track_a):
    markdown = render_markdown(valid_dossier_track_a)

    assert "# Alpha Ltd (ALPHA)" in markdown
    assert "## 1. Identity" in markdown
    assert "## 12. Disconfirming evidence" in markdown
    assert "## 14. Provenance" in markdown
    assert "## 15. Moat & Understandability Memo" in markdown
    assert "## 16. QGLP Scorecard" in markdown
    assert "## 18. Super-Investor Integrity Gate" in markdown
    assert "## 22. Quality-Compounding Checklist" in markdown
    # Track B-only sections must not appear for a Track A dossier.
    assert "## 19. The Davis Double Play Mechanism" not in markdown
    assert "## 24. CANSLIM Momentum Screen Notes" not in markdown


def test_render_markdown_includes_track_b_sections(valid_dossier_track_b):
    markdown = render_markdown(valid_dossier_track_b)

    assert "## 19. The Davis Double Play Mechanism" in markdown
    assert "## 24. CANSLIM Momentum Screen Notes" in markdown
    assert "## 22. Quality-Compounding Checklist" not in markdown


def test_render_markdown_includes_citations(valid_dossier_track_a):
    markdown = render_markdown(valid_dossier_track_a)
    assert "ANNUAL_REPORT_2024" in markdown
    assert "p.12" in markdown
