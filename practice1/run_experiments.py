"""Выполняет задания 2–4 на учебных данных; сохраняет журнал experiments.txt."""
import contextlib
import io
import json
import shutil
import tempfile
import time
from pathlib import Path
import backup as b
from make_test_data import main as generate


def experiment():
    if b.SOURCE.exists() or b.BACKUP_DIR.exists():
        raise ValueError("Эксперимент запускается в чистой копии проекта без company_data и backups")
    generate()
    original = b.make_manifest(b.SOURCE)
    config = b.settings()
    # Для KEEP_LAST=8 нужно не менее 9 запусков, чтобы увидеть ротацию.
    runs = max(8, config["keep_last"] + 1)
    print(f"\nЗадание 2: {runs} запусков, интервал 2 секунды")
    previous = None
    for i in range(runs):
        archive = b.create_backup()
        assert b.verify_restore(archive)
        current = json.loads(b.manifest_path(archive).read_text(encoding="utf-8"))["files"]
        if previous is not None:
            assert current == previous
        previous = current
        b.rotate()
        if i < runs - 1:
            time.sleep(2)
    assert len(list(b.BACKUP_DIR.glob("*.tar.gz"))) == config["keep_last"]
    total = sum(p.stat().st_size for p in b.SOURCE.rglob("*") if p.is_file())
    print(f"Исходные файлы: {total} байт; архив: {archive.stat().st_size} байт; "
          f"коэффициент сжатия: {total / archive.stat().st_size:.2f}")
    print(f"Осталось архивов: {config['keep_last']}; хеши файлов между копиями одинаковы")

    print("\nЗадание 3: изменённый манифест")
    with tempfile.TemporaryDirectory(prefix="damage_demo_", dir=b.BASE) as tmp:
        damaged = Path(tmp) / archive.name
        shutil.copy2(archive, damaged)
        manifest = json.loads(b.manifest_path(archive).read_text(encoding="utf-8"))
        paths = sorted(manifest["files"])
        value = manifest["files"][paths[0]]
        manifest["files"][paths[0]] = ("0" if value[0] != "0" else "1") + value[1:]
        del manifest["files"][paths[1]]
        b.manifest_path(damaged).write_text(json.dumps(manifest), encoding="utf-8")
        assert not b.verify_restore(damaged)
        print("\nПроверка отсутствующего файла (отдельный эксперимент)")
        manifest = json.loads(b.manifest_path(archive).read_text(encoding="utf-8"))
        manifest["files"]["missing_example.csv"] = "0" * 64
        b.manifest_path(damaged).write_text(json.dumps(manifest), encoding="utf-8")
        assert not b.verify_restore(damaged)
        print("\nПовреждённый архив")
        shutil.copy2(b.manifest_path(archive), b.manifest_path(damaged))
        with damaged.open("r+b") as f:
            f.seek(20)
            byte = f.read(1)
            f.seek(20)
            f.write(bytes([byte[0] ^ 255]))
        assert not b.verify_restore(damaged)

    print("\nЗадание 4: удаление отдела и восстановление")
    dept = "buh" if "buh" in config["departments"] else config["departments"][0]
    print(f"Удаляем учебный отдел {dept}; buh отсутствует в варианте: {dept != 'buh'}")
    target = b.SOURCE / dept
    assert target.resolve().parent == b.SOURCE.resolve()
    shutil.rmtree(target)
    assert not target.exists()
    print(f"После инцидента папка {dept} отсутствует: {not target.exists()}")
    b.restore(archive)
    assert target.is_dir() and b.make_manifest(b.SOURCE) == original
    print(f"[OK] Отдел {dept} вернулся; все исходные файлы совпадают по SHA-256")


def main():
    output = io.StringIO()
    try:
        with contextlib.redirect_stdout(output):
            experiment()
    finally:
        text = output.getvalue()
        print(text)
        (b.BASE / "experiments.txt").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
