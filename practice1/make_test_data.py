"""Создаёт учебные файлы отделов по выбранному варианту."""
import random
from backup import SOURCE, settings


def main():
    config = settings()
    rng = random.Random(42)
    if SOURCE.exists() and any(SOURCE.iterdir()):
        raise SystemExit("company_data уже содержит файлы. Для повторной генерации используйте новую папку проекта.")
    for department in config["departments"]:
        folder = SOURCE / department
        folder.mkdir(parents=True, exist_ok=True)
        for i in range(1, config["files_per_department"] + 1):
            lines = [f"{department};doc{i};{rng.randint(1000, 99999)}" for _ in range(200)]
            (folder / f"report_{i}.csv").write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Созданы данные: отделов {len(config['departments'])}; "
          f"файлов {len(config['departments']) * config['files_per_department']}")


if __name__ == "__main__":
    main()
