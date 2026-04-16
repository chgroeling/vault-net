"""Use case for indexing a vault into a domain index."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from pathlib import Path

    from vault_net.domain.models import VaultIndex, VaultLink
    from vault_net.domain.protocols import VaultScanner

logger = structlog.get_logger(__name__)


class IndexVaultUseCase:
    """Orchestrate vault scanning through the scanner port."""

    def __init__(self, scanner: VaultScanner) -> None:
        self._scanner = scanner

    def execute(
        self,
        vault_root: Path,
        *,
        extra_exclude: tuple[str, ...] = (),
        no_default_excludes: bool = False,
    ) -> tuple[VaultIndex, dict[str, list[VaultLink]]]:
        """Scan the vault and return the resulting index with note links."""
        start = time.monotonic()
        logger.debug("use_case.index_vault.start", vault_root=str(vault_root))

        index, note_links = self._scanner.scan(
            vault_root,
            extra_exclude=extra_exclude,
            no_default_excludes=no_default_excludes,
        )

        duration = time.monotonic() - start
        logger.info(
            "use_case.index_vault.complete",
            duration=round(duration, 4),
            total_files=index.metadata.total_files,
        )
        return index, note_links
