"""Настройка варианта: python choose_variant.py 1"""
import argparse
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
# Отделы; файлов на отдел; хранить копий; организация; ГБ; МБ/с;
# интервал копирования (ч); требуемый RPO (ч); требуемый RTO (ч).
ROWS = [
    ("buh sales hr",5,5,"Интернет-магазин",300,150,24,1,2),
    ("it buh legal",6,7,"Поликлиника",800,200,168,4,4),
    ("sales marketing",8,4,"Школа",120,100,24,24,8),
    ("hr buh it sales",4,6,"Банк (филиал)",2048,500,24,.25,1),
    ("dekanat kafedra",7,5,"Университет",1536,250,24,12,6),
    ("sklad buh logistic",5,3,"Склад-логистика",500,120,72,6,3),
    ("clients contracts",10,8,"Нотариальная контора",80,80,168,24,4),
    ("dev qa docs",6,5,"IT-компания",1024,400,24,1,2),
    ("reception lab doctors",5,6,"Лаборатория",250,100,24,2,3),
    ("office shop1 shop2",4,4,"Сеть кафе",60,50,168,24,12),
    ("buh kadry it",6,5,"Строительная компания",400,150,24,8,4),
    ("sales support",7,6,"Колл-центр",200,120,168,2,2),
    ("teachers students admin",5,4,"Колледж",350,100,24,24,12),
    ("pharmacy1 pharmacy2 office",5,7,"Сеть аптек",150,80,72,12,4),
    ("design print buh",6,5,"Типография",900,200,168,24,8),
    ("reception rooms restaurant",4,6,"Гостиница",180,100,24,4,2),
    ("insurance claims buh",6,8,"Страховая компания",1228.8,300,24,1,3),
    ("garage drivers office",5,4,"Автопарк",90,60,168,24,6),
    ("editors video archive",4,3,"Телеканал",5120,600,24,6,4),
    ("akimat con docs",6,7,"Акимат района",700,200,72,12,6),
]


def calculation(number):
    depts, count, keep, org, gb, speed, interval, rpo, rto = ROWS[number - 1]
    seconds = gb * 1024 / speed
    total = seconds + 1800
    return f"""## Вариант {number}: {org}

Данные: {gb:g} ГБ; скорость: {speed} МБ/с; копия каждые {interval:g} ч.
Требования: RPO ≤ {rpo:g} ч; RTO ≤ {rto:g} ч.

Текущий RPO = {interval:g} ч: сбой непосредственно перед очередной успешной копией
может привести к потере всех изменений за этот интервал.
Требование RPO {'выполняется' if interval <= rpo else 'не выполняется'}.

Передача: {gb:g} × 1024 / {speed} = {seconds:.2f} с.
Полное восстановление: {seconds:.2f} + 1800 = {total:.2f} с ≈ {total/60:.2f} мин
(≈ {total/3600:.3f} ч). Требование RTO {'выполняется' if total <= rto*3600 else 'не выполняется'}.

Предложение: создавать успешные точки восстановления не реже одного раза в {rpo:g} ч
с небольшим запасом на длительность и возможный сбой копирования. Для больших объёмов
использовать ежедневную полную копию и промежуточные инкрементные копии или журналы.
После изменения схемы измерить восстановление всей цепочки.

Правило 3-2-1: рабочие данные, локальная резервная копия на отдельном носителе
и ещё одна копия вне здания, например в облачном объектном хранилище с версиями
и ограничением удаления. Использовать два типа носителей, например SSD и HDD.
Регулярно проверять восстановление и доступность внешней копии.
""" + (f"\nДля выполнения RTO при 30 мин подготовки скорость должна быть не ниже "
          f"{gb*1024/(rto*3600-1800):.2f} МБ/с, без учёта дополнительного времени проверки.\n"
          if total > rto*3600 else "")


def select(number):
    depts, count, keep, *_ = ROWS[number - 1]
    source = BASE / "company_data"
    if source.exists() and any(source.iterdir()):
        raise SystemExit("В проекте уже есть данные. Выберите вариант в чистой копии папки practice1.")
    config = dict(variant=number, departments=depts.split(), files_per_department=count, keep_last=keep)
    (BASE / "settings.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    (BASE / "rpo_rto.md").write_text(
        "# Расчёт RPO и RTO\n\nПринято: 1 ТБ = 1024 ГБ; 1 ГБ = 1024 МБ.\n"
        "Расчёт предполагает постоянную скорость, доступную исправную копию и 30 минут подготовки.\n\n"
        + calculation(number), encoding="utf-8")
    print(f"[OK] Выбран вариант {number}; отделы: {depts}; KEEP_LAST={keep}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("variant", type=int, choices=range(1, 21))
    select(p.parse_args().variant)
