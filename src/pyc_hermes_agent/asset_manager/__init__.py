"""Local-first model asset installation helpers."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import uuid4

from pyc_hermes_agent.common import ensure_runtime_directories, resolve_runtime_paths
from pyc_hermes_agent.contracts import ModelAssetManifest

_ASSET_MANIFEST_FILENAME = "pyc_asset_manifest.json"
_SAFE_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass(frozen=True, slots=True)
class InstalledModelAsset:
    manifest: ModelAssetManifest
    asset_dir: Path
    files: tuple[Path, ...]
    checksum: str
    size_bytes: int
    payload_kind: str = "directory"

    @property
    def manifest_path(self) -> Path:
        return self.asset_dir / _ASSET_MANIFEST_FILENAME

    @property
    def primary_path(self) -> Path | None:
        if not self.files:
            return None
        return self.files[0]


class AssetManager:
    def __init__(
        self,
        *,
        root: Path | None = None,
        app_version: str = "0.2.1",
        index_format_version: int = 1,
    ) -> None:
        self._paths = ensure_runtime_directories(resolve_runtime_paths(root))
        self._app_version = app_version
        self._index_format_version = index_format_version

    @property
    def models_dir(self) -> Path:
        return self._paths.models_dir

    @property
    def downloads_dir(self) -> Path:
        return self._paths.downloads_dir

    def get_asset_directory(self, asset_id: str, version: str) -> Path:
        return self.models_dir.joinpath(*_normalize_asset_id(asset_id), _normalize_segment(version, label="version"))

    def get_installed_asset(self, asset_id: str, version: str) -> InstalledModelAsset | None:
        asset_dir = self.get_asset_directory(asset_id, version)
        if not asset_dir.exists():
            return None
        return _read_installed_asset(asset_dir)

    def list_installed_assets(self) -> list[dict[str, object]]:
        """Return inventory entries for every installed model asset under ``models_dir``."""
        models_root = self.models_dir
        if not models_root.exists():
            return []

        inventory: list[dict[str, object]] = []
        for manifest_path in sorted(models_root.rglob(_ASSET_MANIFEST_FILENAME)):
            asset_dir = manifest_path.parent
            try:
                rel = asset_dir.relative_to(models_root)
            except ValueError:  # pragma: no cover - defensive boundary
                continue
            parts = rel.parts
            if len(parts) < 2:
                continue
            version = parts[-1]
            asset_id = "/".join(parts[:-1])
            try:
                installed = _read_installed_asset(asset_dir)
            except ValueError:
                continue
            inventory.append(
                {
                    "asset_id": asset_id,
                    "version": version,
                    "checksum": installed.checksum,
                    "size_bytes": installed.size_bytes,
                    "payload_kind": installed.payload_kind,
                    "primary_path": str(installed.primary_path) if installed.primary_path else None,
                    "manifest": asdict(installed.manifest),
                }
            )
        return inventory

    def install_bytes(
        self,
        manifest: ModelAssetManifest,
        payload: bytes,
        *,
        filename: str = "asset.bin",
    ) -> InstalledModelAsset:
        normalized_filename = _normalize_segment(filename, label="filename")
        _reject_reserved_payload_filename(normalized_filename)
        checksum = calculate_asset_checksum(payload)
        self._validate_install(manifest, checksum=checksum, size_bytes=len(payload))
        target_dir = self.get_asset_directory(manifest.asset_id, manifest.version)
        existing = self.get_installed_asset(manifest.asset_id, manifest.version)
        if existing is not None:
            self._verify_existing_install(existing, manifest)
            return existing

        staging_dir = self._create_staging_dir(manifest)
        try:
            staging_dir.mkdir(parents=True, exist_ok=False)
            (staging_dir / normalized_filename).write_bytes(payload)
            _write_manifest(staging_dir, manifest, payload_kind="file")
            self._promote(staging_dir, target_dir)
        finally:
            if staging_dir.exists():
                shutil.rmtree(staging_dir, ignore_errors=True)

        installed = self.get_installed_asset(manifest.asset_id, manifest.version)
        if installed is None:  # pragma: no cover - defensive boundary
            raise RuntimeError("Installed asset could not be reloaded after promotion.")
        return installed

    def install_path(self, manifest: ModelAssetManifest, source_path: Path) -> InstalledModelAsset:
        source = Path(source_path).resolve()
        if not source.exists():
            raise FileNotFoundError(source)
        if source.is_dir() and (source / _ASSET_MANIFEST_FILENAME).exists():
            raise ValueError(f"Source directory already contains reserved metadata file: {_ASSET_MANIFEST_FILENAME}")
        if source.is_file():
            _reject_reserved_payload_filename(source.name)

        checksum = calculate_asset_checksum(source)
        size_bytes = calculate_asset_size(source)
        self._validate_install(manifest, checksum=checksum, size_bytes=size_bytes)
        target_dir = self.get_asset_directory(manifest.asset_id, manifest.version)
        existing = self.get_installed_asset(manifest.asset_id, manifest.version)
        if existing is not None:
            self._verify_existing_install(existing, manifest)
            return existing

        staging_dir = self._create_staging_dir(manifest)
        try:
            staging_dir.mkdir(parents=True, exist_ok=False)
            if source.is_dir():
                for child in source.iterdir():
                    target = staging_dir / child.name
                    if child.is_dir():
                        shutil.copytree(child, target)
                    else:
                        shutil.copy2(child, target)
            else:
                shutil.copy2(source, staging_dir / source.name)
            _write_manifest(staging_dir, manifest, payload_kind="directory" if source.is_dir() else "file")
            self._promote(staging_dir, target_dir)
        finally:
            if staging_dir.exists():
                shutil.rmtree(staging_dir, ignore_errors=True)

        installed = self.get_installed_asset(manifest.asset_id, manifest.version)
        if installed is None:  # pragma: no cover - defensive boundary
            raise RuntimeError("Installed asset could not be reloaded after promotion.")
        return installed

    def _validate_install(self, manifest: ModelAssetManifest, *, checksum: str, size_bytes: int) -> None:
        _normalize_asset_id(manifest.asset_id)
        _normalize_segment(manifest.version, label="version")
        expected_checksum = _normalize_checksum(manifest.checksum)
        if checksum != expected_checksum:
            raise ValueError("Asset checksum does not match the manifest checksum.")
        if manifest.size_bytes and manifest.size_bytes != size_bytes:
            raise ValueError(f"Asset size does not match the manifest size: expected {manifest.size_bytes}, got {size_bytes}")
        if manifest.compatible_index_format != self._index_format_version:
            raise ValueError(f"Asset index format is incompatible: expected {self._index_format_version}, got {manifest.compatible_index_format}")
        if not _version_satisfies(self._app_version, manifest.compatible_app_range):
            raise ValueError(f"Asset app compatibility range {manifest.compatible_app_range!r} does not include {self._app_version!r}")

    def _verify_existing_install(self, installed: InstalledModelAsset, manifest: ModelAssetManifest) -> None:
        if asdict(installed.manifest) != asdict(manifest):
            raise ValueError("Existing installed asset manifest does not match the requested manifest.")
        if installed.checksum != _normalize_checksum(manifest.checksum):
            raise ValueError("Existing installed asset contents do not match the requested checksum.")
        if manifest.size_bytes and installed.size_bytes != manifest.size_bytes:
            raise ValueError("Existing installed asset size does not match the requested manifest.")

    def _create_staging_dir(self, manifest: ModelAssetManifest) -> Path:
        return self.downloads_dir / "model-staging" / f"stage-{uuid4().hex}"

    def _promote(self, staging_dir: Path, target_dir: Path) -> None:
        if target_dir.exists():
            raise FileExistsError(f"Target asset directory already exists: {target_dir}")
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        staging_dir.replace(target_dir)


def calculate_asset_checksum(source: Path | bytes | bytearray) -> str:
    if isinstance(source, (bytes, bytearray)):
        digest_hex = hashlib.sha256(bytes(source)).hexdigest()
        return f"sha256:{digest_hex}"

    path = Path(source).resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    if path.is_file():
        digest = hashlib.sha256()
        _update_hash_from_file(digest, path)
        return f"sha256:{digest.hexdigest()}"
    if path.is_dir():
        digest = hashlib.sha256()
        for file_path in _iter_asset_files(path):
            relative_path = file_path.relative_to(path).as_posix()
            digest.update(relative_path.encode("utf-8"))
            digest.update(b"\0")
            _update_hash_from_file(digest, file_path)
            digest.update(b"\0")
        return f"sha256:{digest.hexdigest()}"
    raise ValueError(f"Unsupported asset source: {path}")


def calculate_asset_size(source: Path) -> int:
    path = Path(source).resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    if path.is_file():
        return path.stat().st_size
    if path.is_dir():
        return sum(file_path.stat().st_size for file_path in _iter_asset_files(path))
    raise ValueError(f"Unsupported asset source: {path}")


def _iter_asset_files(root: Path) -> list[Path]:
    return sorted(
        (path for path in root.rglob("*") if path.is_file() and path.relative_to(root).as_posix() != _ASSET_MANIFEST_FILENAME),
        key=lambda path: path.relative_to(root).as_posix(),
    )


def _update_hash_from_file(digest: hashlib._Hash, path: Path) -> None:
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                return
            digest.update(chunk)


def _read_installed_asset(asset_dir: Path) -> InstalledModelAsset:
    manifest_path = asset_dir / _ASSET_MANIFEST_FILENAME
    if not manifest_path.exists():
        raise ValueError(f"Installed asset is missing metadata: {manifest_path}")
    metadata = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_payload = metadata.get("manifest", metadata)
    payload_kind = str(metadata.get("payload_kind", "directory"))
    manifest = ModelAssetManifest(**manifest_payload)
    files = tuple(_iter_asset_files(asset_dir))
    return InstalledModelAsset(
        manifest=manifest,
        asset_dir=asset_dir,
        files=files,
        checksum=_calculate_installed_checksum(asset_dir, files, payload_kind),
        size_bytes=calculate_asset_size(asset_dir),
        payload_kind=payload_kind,
    )


def _write_manifest(asset_dir: Path, manifest: ModelAssetManifest, *, payload_kind: str) -> None:
    (asset_dir / _ASSET_MANIFEST_FILENAME).write_text(
        json.dumps(
            {
                "manifest": asdict(manifest),
                "payload_kind": payload_kind,
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )


def _calculate_installed_checksum(asset_dir: Path, files: tuple[Path, ...], payload_kind: str) -> str:
    if payload_kind == "file":
        if len(files) != 1:
            raise ValueError(f"Installed file asset must contain exactly one payload file: {asset_dir}")
        return calculate_asset_checksum(files[0])
    return calculate_asset_checksum(asset_dir)


def _normalize_asset_id(asset_id: str) -> tuple[str, ...]:
    normalized = asset_id.replace("\\", "/")
    parts = tuple(part for part in normalized.split("/") if part)
    if not parts:
        raise ValueError("Asset id must not be empty.")
    for part in parts:
        _normalize_segment(part, label="asset id segment")
    return parts


def _normalize_segment(value: str, *, label: str) -> str:
    normalized = value.strip()
    if normalized in {"", ".", ".."} or not _SAFE_SEGMENT_RE.fullmatch(normalized):
        raise ValueError(f"Invalid {label}: {value!r}")
    return normalized


def _reject_reserved_payload_filename(filename: str) -> None:
    if filename == _ASSET_MANIFEST_FILENAME:
        raise ValueError(f"Asset payload filename uses reserved metadata file: {_ASSET_MANIFEST_FILENAME}")


def _normalize_checksum(value: str) -> str:
    normalized = value.strip().lower()
    if normalized.startswith("sha256:"):
        normalized = normalized[7:]
    if not re.fullmatch(r"[0-9a-f]{64}", normalized):
        raise ValueError(f"Unsupported checksum format: {value!r}")
    return f"sha256:{normalized}"


def _version_satisfies(version: str, spec: str) -> bool:
    if not spec.strip():
        return True
    current = _parse_version(version)
    for clause in (item.strip() for item in spec.split(",") if item.strip()):
        operator = next((candidate for candidate in (">=", "<=", "==", ">", "<") if clause.startswith(candidate)), None)
        if operator is None:
            raise ValueError(f"Unsupported version clause: {clause!r}")
        target = _parse_version(clause[len(operator) :].strip())
        comparison = _compare_versions(current, target)
        if operator == ">=" and comparison < 0:
            return False
        if operator == "<=" and comparison > 0:
            return False
        if operator == "==" and comparison != 0:
            return False
        if operator == ">" and comparison <= 0:
            return False
        if operator == "<" and comparison >= 0:
            return False
    return True


def _parse_version(value: str) -> tuple[int, ...]:
    parts = tuple(part for part in value.strip().split(".") if part)
    if not parts or any(not part.isdigit() for part in parts):
        raise ValueError(f"Unsupported version string: {value!r}")
    return tuple(int(part) for part in parts)


def _compare_versions(left: tuple[int, ...], right: tuple[int, ...]) -> int:
    max_length = max(len(left), len(right))
    padded_left = left + (0,) * (max_length - len(left))
    padded_right = right + (0,) * (max_length - len(right))
    if padded_left < padded_right:
        return -1
    if padded_left > padded_right:
        return 1
    return 0


__all__ = [
    "AssetManager",
    "InstalledModelAsset",
    "calculate_asset_checksum",
    "calculate_asset_size",
]
