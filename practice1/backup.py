"""Полные резервные копии, ротация, проверка и восстановление (Python 3.12+)."""
import argparse
import hashlib
import json
import shutil
import tarfile
import tempfile
import time
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
SOURCE = BASE / "company_data"
BACKUP_DIR = BASE / "backups"


def settings():
    return json.loads((BASE / "settings.json").read_text(encoding="utf-8"))


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def make_manifest(folder):
    return {p.relative_to(folder).as_posix(): sha256(p)
            for p in sorted(folder.rglob("*")) if p.is_file()}


def manifest_path(archive):
    return archive.with_suffix("").with_suffix(".json")


def create_backup():
    if not SOURCE.is_dir() or not any(SOURCE.rglob("*.csv")):
        raise ValueError("Сначала запустите make_test_data.py")
    BACKUP_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    archive = BACKUP_DIR / f"backup_{stamp}.tar.gz"
    files = make_manifest(SOURCE)
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(SOURCE, arcname=SOURCE.name)
    manifest = {"created": stamp, "archive_sha256": sha256(archive), "files": files}
    manifest_path(archive).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] Создан {archive.name}; файлов: {len(files)}; байт: {archive.stat().st_size}")
    return archive


def rotate():
    keep = settings()["keep_last"]
    if not isinstance(keep, int) or keep < 1:
        raise ValueError("keep_last должен быть положительным целым числом")
    for old in sorted(BACKUP_DIR.glob("backup_*.tar.gz"))[:-keep]:
        old.unlink()
        manifest_path(old).unlink(missing_ok=True)
        print(f"[ROTATE] Удалена копия {old.name}")


def differences(expected, restored):
    missing = sorted(expected.keys() - restored.keys())
    extra = sorted(restored.keys() - expected.keys())
    changed = sorted(p for p in expected.keys() & restored.keys()
                     if expected[p] != restored[p])
    for label, paths in [("ОТСУТСТВУЕТ", missing), ("ЛИШНИЙ", extra), ("ИЗМЕНЁН", changed)]:
        for path in paths:
            print(f"[{label}] {path}")
    return missing, extra, changed


def unpack_checked(archive, destination):
    # Учебные копии содержат только обычные файлы и каталоги company_data.
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar.getmembers():
            parts = Path(member.name).parts
            if (not parts or parts[0] != SOURCE.name or ".." in parts
                    or not (member.isfile() or member.isdir())):
                raise ValueError(f"Недопустимый объект архива: {member.name}")
        tar.extractall(destination, filter="data")


def verify_restore(archive):
    archive = Path(archive)
    try:
        manifest = json.loads(manifest_path(archive).read_text(encoding="utf-8"))
        if sha256(archive) != manifest["archive_sha256"]:
            print("[FAIL] Архив повреждён: контрольная сумма не совпадает")
            return False
        with tempfile.TemporaryDirectory(prefix="restore_test_", dir=BASE) as tmp:
            unpack_checked(archive, tmp)
            restored = make_manifest(Path(tmp) / SOURCE.name)
        if any(differences(manifest["files"], restored)):
            print("[FAIL] Восстановленные данные не совпадают с манифестом")
            return False
        print(f"[OK] Восстановление проверено: {len(restored)} файлов совпадают")
        return True
    except (OSError, ValueError, KeyError, TypeError, tarfile.TarError, EOFError) as exc:
        print(f"[FAIL] Проверка не выполнена: {exc}")
        return False


def restore(archive):
    started = time.perf_counter()
    # Проверяем выбранную копию до удаления текущих тестовых данных.
    if not verify_restore(archive):
        raise ValueError("Восстановление отменено: копия не прошла проверку")
    if SOURCE.resolve() != BASE / "company_data":
        raise ValueError("Некорректный путь к тестовым данным")
    if SOURCE.exists():
        shutil.rmtree(SOURCE)
    unpack_checked(Path(archive), BASE)
    expected = json.loads(manifest_path(Path(archive)).read_text(encoding="utf-8"))["files"]
    if make_manifest(SOURCE) != expected:
        raise ValueError("Ошибка проверки восстановленных данных")
    elapsed = time.perf_counter() - started
    print(f"[OK] Данные восстановлены; время с проверкой: {elapsed:.6f} с")
    return elapsed


def latest():
    archives = sorted(BACKUP_DIR.glob("backup_*.tar.gz"))
    if not archives:
        raise ValueError("Нет резервных копий")
    return archives[-1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", choices=["backup", "verify", "restore"], default="backup")
    parser.add_argument("archive", nargs="?", help="Путь к архиву; по умолчанию последний")
    args = parser.parse_args()
    try:
        if args.action == "backup":
            archive = create_backup()
            if not verify_restore(archive):
                return 1
            rotate()
        else:
            archive = Path(args.archive).resolve() if args.archive else latest()
            if args.action == "verify":
                return 0 if verify_restore(archive) else 1
            restore(archive)
        return 0
    except (OSError, ValueError, tarfile.TarError) as exc:
        print(f"[FAIL] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
