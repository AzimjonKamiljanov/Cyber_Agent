"""Unit tests for SQLite FTS5 Memory Engine and tools (Stage S5)."""

from pathlib import Path

import pytest

from cyber_agent.memory.filters import check_for_secrets
from cyber_agent.memory.repository import MemoryRepository
from cyber_agent.tools.memory.tools import (
    handle_memory_forget,
    handle_memory_list,
    handle_memory_recall,
    handle_memory_remember,
    handle_memory_wipe,
)
from cyber_agent.tools.schemas import (
    MemoryForgetArgs,
    MemoryListArgs,
    MemoryRecallArgs,
    MemoryRememberArgs,
    MemoryWipeArgs,
)


@pytest.fixture
def test_repo(tmp_path: Path) -> MemoryRepository:
    db_file = tmp_path / "test_memory.sqlite3"
    return MemoryRepository(db_path=db_file)


def test_secret_filtering() -> None:
    """Ensure sensitive credentials and card numbers are blocked."""
    assert check_for_secrets("My password is safe123")[0] is False
    assert check_for_secrets("parol: superSecret123")[0] is True
    assert check_for_secrets("paroli: 999abc")[0] is True
    assert check_for_secrets("PIN: 4589")[0] is True
    assert check_for_secrets("AIzaSyD1234567890abcdef1234567890abcdef")[0] is True
    assert check_for_secrets("sk-1234567890abcdef1234567890abcdef")[0] is True
    assert check_for_secrets("8600 1234 5678 9012")[0] is True
    assert check_for_secrets("9860 9999 8888 7777")[0] is True


def test_memory_crud_and_fts5_search(test_repo: MemoryRepository) -> None:
    """Test inserting, FTS5 recall, listing, and forgetting."""
    # 1. Insert memories
    ok1, _, id1 = test_repo.remember("Azimjonning ish stoli GNOME 50 Wayland", consent=True)
    ok2, _, id2 = test_repo.remember("Toshkentda havo harorati bahorda juda go'zal", consent=True)
    ok3, _, _id3 = test_repo.remember("Cyber Agent shaxsiy ovozli yordamchi tizimi", consent=True)
    assert ok1 and ok2 and ok3

    # 2. FTS5 Search
    matches_gnome = test_repo.recall("Wayland")
    assert len(matches_gnome) == 1
    assert matches_gnome[0].id == id1

    matches_tashkent = test_repo.recall("Toshkentda")
    assert len(matches_tashkent) == 1
    assert matches_tashkent[0].id == id2

    # 3. List memories
    all_items = test_repo.list_memories()
    assert len(all_items) == 3

    # 4. Forget item
    assert id1 is not None
    del_ok, _ = test_repo.forget(id1)
    assert del_ok is True
    assert len(test_repo.recall("Wayland")) == 0

    # 5. Wipe remaining
    wipe_ok, count = test_repo.wipe()
    assert wipe_ok is True
    assert count == 2
    assert len(test_repo.list_memories()) == 0


@pytest.mark.asyncio
async def test_memory_tool_handlers(test_repo: MemoryRepository, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test tool handlers with monkeypatched repository."""
    monkeypatch.setattr("cyber_agent.tools.memory.tools.get_memory_repository", lambda: test_repo)

    # Remember
    res_rem = await handle_memory_remember(
        MemoryRememberArgs(text="Ertaga ertalab soat 9 da uchrashuv bor")
    )
    assert res_rem.success is True
    assert "Eslab qolindi" in res_rem.output

    # Recall
    res_rec = await handle_memory_recall(MemoryRecallArgs(query="uchrashuv"))
    assert res_rec.success is True
    assert "Ertaga ertalab" in res_rec.output
    assert "[XOTIRADAGI MA'LUMOTLAR - FAQAT O'QISH UCHUN]" in res_rec.output

    # List
    res_list = await handle_memory_list(MemoryListArgs())
    assert res_list.success is True
    assert "1. Ertaga ertalab" in res_list.output

    # Forget
    res_forg = await handle_memory_forget(MemoryForgetArgs(target="uchrashuv"))
    assert res_forg.success is True

    # Wipe
    res_wipe = await handle_memory_wipe(MemoryWipeArgs(confirm=True))
    assert res_wipe.success is True
    assert "o'chirildi" in res_wipe.output
