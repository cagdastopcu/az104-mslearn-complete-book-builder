from __future__ import annotations

import random

from generate_az104_examstyle_chapter_test_book import Fact, _format_question


def test_choose_two_falls_back_when_no_same_section_pair() -> None:
    facts = [
        Fact("Azure policy can enforce tag rules on resources.", "Policy"),
        Fact("Azure Monitor can collect platform metrics from resources.", "Monitoring"),
        Fact("Azure RBAC controls access to management operations.", "Access"),
        Fact("Azure backup can protect virtual machines.", "Backup"),
        Fact("Azure DNS hosts public and private DNS zones.", "Networking"),
    ]
    target = facts[1]
    distractors = [facts[0], facts[2], facts[3]]

    rendered = _format_question(
        chapter_question_no=2,
        subtitle="Ops",
        target=target,
        facts=facts,
        distractors=distractors,
        rng=random.Random(7),
    )

    assert "**Item type:** Choose TWO." not in rendered
    assert "**Item type:** Single best answer." in rendered


def test_true_false_falls_back_when_no_alternate_section() -> None:
    facts = [
        Fact("Azure RBAC can scope assignments at resource group level.", "Access"),
        Fact("Azure RBAC can scope assignments at subscription level.", "Access"),
        Fact("Azure RBAC roles define allowed management actions.", "Access"),
        Fact("Azure RBAC changes should follow least privilege.", "Access"),
    ]
    target = facts[0]
    distractors = [facts[1], facts[2], facts[3]]

    rendered = _format_question(
        chapter_question_no=4,
        subtitle="Access Control",
        target=target,
        facts=facts,
        distractors=distractors,
        rng=random.Random(11),
    )

    assert "**Item type:** True/False combination." not in rendered
    assert "**Item type:** Single best answer." in rendered

