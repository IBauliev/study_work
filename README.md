# Apache Log Analyzer - Краткое руководство

## Установка
```bash
pip install -r requirements.txt
```

## Основные команды

1. **Парсинг логов** (из файла access.log в папке logs):
```bash
python cli.py parse
```

2. **Просмотр всех логов** (первые 100 записей):
```bash
python cli.py show
```

3. **Фильтрация логов**:
```bash
# По IP-адресу
python cli.py show --ip 192.168.1.1

# По ключевому слову в URL
python cli.py show --keyword admin

# За определенный период
python cli.py show --date-from 2023-01-01 --date-to 2023-12-31

# С лимитом записей
python cli.py show --limit 50
```

## Где лежат файлы
- Логи по умолчанию: `./logs/access.log`
- База данных: `./logs.db`
- Конфиг: `./config.ini`