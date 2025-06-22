import sqlite3
import configparser
import os
import re
import sys
from datetime import datetime
import argparse
from tqdm import tqdm
import time

class LogAnalyzer:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.load_config()
        self.db_path = self.config['Database']['URI'].replace('sqlite:///', '')
        self.init_db()

    def load_config(self):
        """Загрузка или создание конфига"""
        self.config.read('config.ini')
        
        if not self.config.sections():
            self.config['Database'] = {'URI': 'sqlite:///logs.db'}
            self.config['Logs'] = {'Directory': 'logs', 'Pattern': 'access.log'}
            with open('config.ini', 'w') as f:
                self.config.write(f)

    def init_db(self):
        """Инициализация базы данных"""
        if os.path.dirname(self.db_path):
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS log_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT,
                date TEXT,
                method TEXT,
                url TEXT,
                status INTEGER,
                size INTEGER,
                user_agent TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def parse_log_file(self):
        """Парсинг лог-файла с прогресс-баром"""
        log_path = os.path.join(
            self.config['Logs']['Directory'],
            self.config['Logs']['Pattern']
        )
        
        if not os.path.exists(log_path):
            print(f"Ошибка: Файл логов не найден: {log_path}")
            return False

        with open(log_path, 'r', encoding='utf-8') as f:
            total_lines = sum(1 for _ in f)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        parsed_count = 0

        print(f"\nПарсинг файла: {log_path}")
        with tqdm(total=total_lines, desc="Прогресс", unit="line") as pbar:
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        parsed = self.parse_line(line.strip())
                        if parsed:
                            cursor.execute('''
                                INSERT INTO log_entries 
                                (ip, date, method, url, status, size, user_agent)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            ''', parsed)
                            parsed_count += 1
                    except Exception as e:
                        print(f"\nОшибка в строке: {e}", file=sys.stderr)
                    finally:
                        pbar.update(1)
                        time.sleep(0.001)  

        conn.commit()
        conn.close()
        print(f"\nГотово! Обработано строк: {parsed_count}/{total_lines}")
        return True

    def parse_line(self, line):
        """Парсинг одной строки лога"""
        match = re.match(
            r'^(\S+) \S+ \S+ \[(.*?)\] "(.*?)" (\d+) (\d+) "(.*?)" "(.*?)"',
            line
        )
        if not match:
            return None

        ip, date_str, req, status, size, referrer, ua = match.groups()
        method, url, _ = req.split(' ', 2)
        
        try:
            date = datetime.strptime(date_str, '%d/%b/%Y:%H:%M:%S %z').isoformat()
        except:
            date = date_str

        return (
            ip,
            date,
            method,
            url,
            int(status),
            int(size),
            ua if ua != '-' else None
        )

    def show_logs(self, filters):
        """Вывод логов с фильтрацией"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        where_clauses = []
        params = []

        if filters.get('ip'):
            where_clauses.append("ip = ?")
            params.append(filters['ip'])
        if filters.get('keyword'):
            where_clauses.append("url LIKE ?")
            params.append(f"%{filters['keyword']}%")
        if filters.get('date_from'):
            where_clauses.append("date >= ?")
            params.append(filters['date_from'])
        if filters.get('date_to'):
            where_clauses.append("date <= ?")
            params.append(filters['date_to'])

        where = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        limit = f"LIMIT {filters.get('limit', 100)}"

        query = f"SELECT * FROM log_entries {where} ORDER BY date DESC {limit}"
        
        cursor.execute(query, params)
        logs = cursor.fetchall()

        if not logs:
            print("Логи не найдены")
            return

        print("\nРезультаты:")
        print("-" * 120)
        print(f"| {'IP':<15} | {'Дата':<20} | {'Метод':<6} | {'URL':<40} | {'Статус':<6} | {'Размер':<6} |")
        print("-" * 120)
        
        for log in logs:
            print(f"| {log[1]:<15} | {log[2][:19]:<20} | {log[3]:<6} | {log[4][:40]:<40} | {log[5]:<6} | {log[6]:<6} |")
        
        print("-" * 120)
        print(f"Всего найдено: {len(logs)}")
        conn.close()

def main():
    parser = argparse.ArgumentParser(description='Apache Log Analyzer CLI')
    subparsers = parser.add_subparsers(dest='command', required=True)

    parse_parser = subparsers.add_parser('parse', help='Парсинг лог-файла')

    show_parser = subparsers.add_parser('show', help='Просмотр логов')
    show_parser.add_argument('--ip', help='Фильтр по IP')
    show_parser.add_argument('--keyword', help='Поиск по ключевому слову в URL')
    show_parser.add_argument('--date-from', help='Фильтр по дате (с) YYYY-MM-DD')
    show_parser.add_argument('--date-to', help='Фильтр по дате (по) YYYY-MM-DD')
    show_parser.add_argument('--limit', type=int, default=100, help='Лимит записей')

    args = parser.parse_args()
    analyzer = LogAnalyzer()

    if args.command == 'parse':
        analyzer.parse_log_file()
    elif args.command == 'show':
        analyzer.show_logs({
            'ip': args.ip,
            'keyword': args.keyword,
            'date_from': args.date_from,
            'date_to': args.date_to,
            'limit': args.limit
        })

if __name__ == '__main__':
    main()
