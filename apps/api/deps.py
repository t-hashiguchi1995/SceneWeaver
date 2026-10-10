from __future__ import annotations

from creator_studio.infrastructure.container import Container, get_container


def container() -> Container:
    return get_container()