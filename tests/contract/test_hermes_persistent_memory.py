from pyc_hermes_agent.hermes_engine import PersistentMemorySnapshot, PersistentMemoryStore


def test_persistent_memory_store_persists_memory_and_user_entries_separately(tmp_path) -> None:
    store = PersistentMemoryStore(root=tmp_path)

    memory_entries = store.append("memory", "Project prefers concise outputs")
    user_entries = store.append("user", "User prefers markdown tables")

    assert memory_entries == ["Project prefers concise outputs"]
    assert user_entries == ["User prefers markdown tables"]
    assert store.resolve_path("memory").name == "MEMORY.md"
    assert store.resolve_path("user").name == "USER.md"
    assert store.load_entries("memory") == ["Project prefers concise outputs"]
    assert store.load_entries("user") == ["User prefers markdown tables"]


def test_persistent_memory_store_replaces_and_removes_entries_by_unique_substring(tmp_path) -> None:
    store = PersistentMemoryStore(root=tmp_path)
    store.save_entries("memory", ["Alpha note", "Beta note"])

    replaced = store.replace("memory", "Alpha", "Alpha updated")
    remaining = store.remove("memory", "Beta")

    assert replaced == ["Alpha updated", "Beta note"]
    assert remaining == ["Alpha updated"]


def test_persistent_memory_store_loads_snapshot_and_formats_system_prompt_blocks(tmp_path) -> None:
    store = PersistentMemoryStore(root=tmp_path)
    store.save_entries("memory", ["Remember the workspace conventions"])
    store.save_entries("user", ["The user likes concise replies"])

    snapshot = store.load_snapshot()

    assert isinstance(snapshot, PersistentMemorySnapshot)
    assert snapshot.memory_entries == ("Remember the workspace conventions",)
    assert snapshot.user_entries == ("The user likes concise replies",)
    assert store.format_for_system_prompt("memory") == "MEMORY (persistent notes)\nRemember the workspace conventions"
    assert store.format_for_system_prompt("user") == "USER PROFILE (persistent preferences)\nThe user likes concise replies"
