"""Multi-strategy locator generator for HTML DOM elements.

Synthesizes resilient alternative locators (data attributes, stable IDs,
accessible roles/names, unique text, semantic CSS, and hierarchical selectors).
"""

from __future__ import annotations

import re
from typing import Generator
from bs4 import BeautifulSoup, Tag

from self_healing.models import RepairStrategy


# Attributes recognized as dedicated, high-stability test hooks
DATA_TEST_ATTRIBUTES = [
    "data-testid",
    "data-test-id",
    "data-test",
    "data-cy",
    "data-qa",
    "data-id",
    "data-automation-id",
]

# Patterns indicating dynamic, auto-generated, or volatile ID values
VOLATILE_ID_PATTERNS = [
    re.compile(r"^[0-9a-f]{8,}", re.IGNORECASE),          # hex hashes
    re.compile(r"^\d+$"),                                 # purely numeric
    re.compile(r"^ember\d+", re.IGNORECASE),              # Ember auto-ids
    re.compile(r"^react-select-\d+"),                     # React-select dynamic ids
    re.compile(r":r[0-9a-z]+:"),                          # React 18 useId
    re.compile(r"^ng-\w+"),                               # Angular auto
    re.compile(r"-\d{4,}$"),                              # trailing timestamp/rand
]

# Ephemeral UI state class names to avoid in semantic CSS selectors
TRANSIENT_CLASSES = {
    "active", "is-active", "hover", "focus", "selected", "disabled",
    "loading", "is-loading", "open", "is-open", "show", "hide", "hidden",
    "ng-dirty", "ng-touched", "ng-pristine", "ng-valid", "ng-invalid",
}


def is_stable_id(element_id: str) -> bool:
    """Return True if element_id appears human-authored and structurally stable."""
    if not element_id or len(element_id) < 2:
        return False
    for pat in VOLATILE_ID_PATTERNS:
        if pat.search(element_id):
            return False
    return True


def generate_candidate_locators_for_element(
    element: Tag,
    soup: BeautifulSoup,
) -> list[tuple[str, RepairStrategy, str]]:
    """Synthesize candidate locators for a specific DOM Tag.

    Returns:
        List of (selector, strategy, explanation) tuples.
    """
    candidates: list[tuple[str, RepairStrategy, str]] = []
    tag_name = element.name.lower()
    attrs = element.attrs

    # 1. Strategy: Data Attributes (Highest Testing Resilience)
    for attr in DATA_TEST_ATTRIBUTES:
        val = attrs.get(attr)
        if val and isinstance(val, str) and val.strip():
            clean_val = val.strip()
            # Naked attribute selector
            candidates.append((
                f'[{attr}="{clean_val}"]',
                RepairStrategy.DATA_ATTRIBUTE,
                f"Resilient test hook '{attr}=\"{clean_val}\"'"
            ))
            # Tag-qualified attribute selector
            candidates.append((
                f'{tag_name}[{attr}="{clean_val}"]',
                RepairStrategy.DATA_ATTRIBUTE,
                f"Tag-qualified test hook '{tag_name}[{attr}=\"{clean_val}\"]'"
            ))

    # 2. Strategy: Stable ID
    elem_id = attrs.get("id")
    if elem_id and isinstance(elem_id, str) and is_stable_id(elem_id.strip()):
        clean_id = elem_id.strip()
        candidates.append((
            f"#{clean_id}",
            RepairStrategy.STABLE_ID,
            f"Stable element ID '#{clean_id}'"
        ))
        candidates.append((
            f"{tag_name}#{clean_id}",
            RepairStrategy.STABLE_ID,
            f"Tag-qualified element ID '{tag_name}#{clean_id}'"
        ))

    # 3. Strategy: Accessible Roles and ARIA Labels
    aria_label = attrs.get("aria-label")
    if aria_label and isinstance(aria_label, str) and aria_label.strip():
        clean_label = aria_label.strip()
        candidates.append((
            f'{tag_name}[aria-label="{clean_label}"]',
            RepairStrategy.ACCESSIBLE_ROLE_NAME,
            f"Accessible label on <{tag_name}>: '{clean_label}'"
        ))

    role = attrs.get("role")
    if role and isinstance(role, str) and aria_label:
        clean_role = role.strip()
        candidates.append((
            f'[role="{clean_role}"][aria-label="{aria_label.strip()}"]',
            RepairStrategy.ACCESSIBLE_ROLE_NAME,
            f"Accessible role '{clean_role}' with label '{aria_label.strip()}'"
        ))

    # Title attribute fallback for accessible tooltip/hover
    title_val = attrs.get("title")
    if title_val and isinstance(title_val, str) and title_val.strip():
        candidates.append((
            f'{tag_name}[title="{title_val.strip()}"]',
            RepairStrategy.ACCESSIBLE_ROLE_NAME,
            f"Accessible title attribute '{title_val.strip()}'"
        ))

    # 4. Strategy: Unique Clean Text (Buttons, Links, Headings)
    if tag_name in {"button", "a", "label", "span", "h1", "h2", "h3", "h4", "p"}:
        text_content = element.get_text(separator=" ", strip=True)
        # Filter clean short text (3 to 60 characters, no line breaks)
        if text_content and 3 <= len(text_content) <= 60 and "\n" not in text_content:
            # Escape quotes for selector
            escaped_text = text_content.replace('"', '\\"')
            candidates.append((
                f'{tag_name}:has-text("{escaped_text}")',
                RepairStrategy.UNIQUE_TEXT,
                f"Element with unique inner text: '{text_content}'"
            ))

    # 5. Strategy: Semantic CSS Classes
    classes = attrs.get("class")
    if classes:
        if isinstance(classes, str):
            class_list = classes.split()
        else:
            class_list = list(classes)

        # Filter out transient state classes
        meaningful_classes = [c.strip() for c in class_list if c.strip() and c.strip().lower() not in TRANSIENT_CLASSES]

        if meaningful_classes:
            # Full class combination
            full_class_str = "." + ".".join(meaningful_classes)
            candidates.append((
                f"{tag_name}{full_class_str}",
                RepairStrategy.SEMANTIC_CSS,
                f"Tag with semantic CSS class combination '{tag_name}{full_class_str}'"
            ))

            # Individual distinctive classes if multiple
            if len(meaningful_classes) > 1:
                # Last or distinctive class often represents the component identifier
                for distinctive in reversed(meaningful_classes):
                    if len(distinctive) >= 4 and not distinctive.startswith("btn-"):
                        candidates.append((
                            f"{tag_name}.{distinctive}",
                            RepairStrategy.SEMANTIC_CSS,
                            f"Specific semantic component class '{tag_name}.{distinctive}'"
                        ))
                        break

    # 6. Strategy: Hierarchical / Container Scope
    parent = element.parent
    if parent and isinstance(parent, Tag) and parent.name != "[document]":
        parent_id = parent.get("id")
        if parent_id and isinstance(parent_id, str) and is_stable_id(parent_id.strip()):
            p_id = parent_id.strip()
            # Try combining parent ID with child tag/class
            if meaningful_classes := [c for c in (attrs.get("class") or []) if c not in TRANSIENT_CLASSES]:
                candidates.append((
                    f"#{p_id} > {tag_name}.{meaningful_classes[0]}",
                    RepairStrategy.HIERARCHICAL,
                    f"Scoped child selector under parent container '#{p_id}'"
                ))
            else:
                candidates.append((
                    f"#{p_id} > {tag_name}",
                    RepairStrategy.HIERARCHICAL,
                    f"Scoped direct child under parent container '#{p_id}'"
                ))

    return candidates
