#!/usr/bin/env python3
"""Render existing execution records; never invent pipeline statuses or outputs."""
from collections import Counter
from datetime import datetime
import html
import json
from pathlib import Path
from zoneinfo import ZoneInfo

LAB = Path(__file__).resolve().parent
OUT = LAB / 'evidence'


def read(path):
    return json.loads(path.read_text())


def escaped(value):
    return html.escape(str(value))


def main():
    runs = [read(OUT / name / 'run.json') for name in ['red-code-final', 'red-security-final', 'green-final']]
    before = read(OUT / 'frontend-before.json')
    before_counts = Counter(v['Severity'] for result in before.get('Results', []) for v in result.get('Vulnerabilities', []))
    old_frontend = {'HIGH': before_counts['HIGH'], 'CRITICAL': before_counts['CRITICAL']}
    bad = read(OUT / 'bad-pipeline/result.json')
    broken_path = sorted(OUT.glob('broken-release-*/demonstration.json'))[-1]
    broken = read(broken_path)
    rollback = read(LAB / broken['rollback_evidence'] / 'rollback.json')
    sections = []
    titles = ['Регрессия в коде — деплой заблокирован', 'CRITICAL — публикация и деплой заблокированы', 'Полный успешный прогон']
    for run, title in zip(runs, titles):
        if run['status'] == 'failed':
            assert run['deployment_before'] == run['deployment_after']
        started = datetime.fromisoformat(run['started_at']).astimezone(ZoneInfo('Europe/Moscow')).strftime('%d.%m.%Y %H:%M:%S МСК')
        stages = ''.join(f'<div class="stage {escaped(item["status"])}"><b>{escaped(stage)}</b><span>{escaped(item["status"])}</span><small>{item.get("seconds", "—")} с</small></div>' for stage, item in run['stages'].items())
        links = ' · '.join(f'<a href="{run["id"]}/{stage}.log">{stage}.log</a>' for stage, record in run['stages'].items() if record['status'] in ['passed', 'failed'])
        note = 'Работающие контейнеры до и после прогона совпадают.' if run['status'] == 'failed' else 'Просканированные образы опубликованы, сервис и PostgreSQL проверены.'
        sections.append(f'<section><h2>{title}</h2><p>{started} · исполнение: {run["execution"]} · <a href="{run["id"]}/run.json">исходный run.json</a></p><div class="stages">{stages}</div><p>{note}</p><p>{links}</p></section>')
    rows = [
        ('Старый backend', runs[1]['security']['backend']),
        ('Исправленный backend', runs[2]['security']['backend']),
        ('Frontend до обновления', old_frontend),
        ('Frontend после обновления', runs[2]['security']['frontend']),
    ]
    table = ''.join(f'<tr><td>{label}</td><td>{data["CRITICAL"]}</td><td>{data["HIGH"]}</td></tr>' for label, data in rows)
    sections.append('<section><h2>Результаты Trivy</h2><table><tr><th>Образ</th><th>CRITICAL</th><th>HIGH</th></tr>' + table + '</table><p>Число находок по пакетам; одна CVE может встречаться в нескольких пакетах. Оставшиеся HIGH не скрыты.</p><p>Обновлены brotli-libs 1.2.1-r0, curl/libcurl 8.23.0-r0. У 44 HIGH Debian поле FixedVersion пустое.</p></section>')
    sections.append(f'<section><h2>Плохой пайплайн действительно деплоит регрессию</h2><p>Код завершения проигнорированного теста: <b>{bad["ignored_test_exit_code"]}</b>. Сканирование: <b>{bad["security_scan"]}</b>. Регистрация после деплоя: <b>{bad["observed_registration_status"]}</b>; вход с верным паролем: <b>{bad["observed_login_status"]}</b>.</p><p><a href="bad-pipeline/result.json">Результат наблюдения</a> · <a href="bad-pipeline/pipeline.log">Фактический протокол</a></p></section>')
    relative_broken = str(broken_path.parent.relative_to(OUT))
    relative_rollback = str(Path(broken['rollback_evidence']).relative_to('evidence'))
    sections.append(f'<section><h2>Неисправный релиз → откат → работающий сервис</h2><p>Неисправная версия: <code>{escaped(broken["broken_version"])}</code>.</p><p>Восстановлено: <code>{escaped(broken["restored_version"])}</code>.</p><p class="metric">Откат: {rollback["seconds"]:.3f} с</p><p><a href="{relative_broken}/broken-release.log">Ошибка запуска и неуспешный curl</a> · <a href="{relative_rollback}/rollback.log">Откат и успешный curl</a></p></section>')
    sections.append('<section><h2>Фактическая проверка развёрнутого сервиса</h2><pre>' + escaped((OUT / 'green-final/verify.log').read_text()) + '</pre></section>')
    styles = '''body{max-width:1420px;margin:36px auto;padding:0 20px;font:18px/1.5 system-ui;color:#1d2738;background:#f5f7fa}h1{font-size:34px}h2{font-size:23px}section{background:white;border:1px solid #dde2ea;border-radius:12px;padding:22px;margin:20px 0}p{overflow-wrap:anywhere}a{color:#1756b0}.stages{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px}.stage{display:flex;flex-direction:column;border-radius:6px;padding:12px;background:#e8edf2}.passed{background:#d9f3e1;color:#14532d}.failed{background:#fee0df;color:#991b1b}.skipped{color:#5c6674}.stage small{opacity:.8}table{border-collapse:collapse;width:100%}td,th{border:1px solid #d8dde5;padding:12px;text-align:left}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f2f4f7;padding:16px;font:14px/1.6 ui-monospace,monospace}.metric{font-size:27px;font-weight:700}code{font-size:15px}header p{color:#4d596b}'''
    document = '<!doctype html><html lang="ru"><meta charset="utf-8"><title>Лабораторная 3 Локальная проверка CI CD</title><style>' + styles + '</style><header><h1>Лабораторная 3 — локальная проверка CI/CD</h1><p>Сформировано из фактических JSON и логов локальных проверок до публикации работы. Данные этого отчёта не являются результатами GitHub Actions.</p></header>' + ''.join(sections) + '</html>'
    (OUT / 'index.html').write_text(document)
    dump = {'execution': 'local', 'github_actions_executed': False, 'runs': [{'id': run['id'], 'scenario': run['scenario'], 'status': run['status'], 'stages': {name: item['status'] for name, item in run['stages'].items()}} for run in runs], 'security': {name: data for name, data in rows}, 'rollback': rollback, 'bad_pipeline': bad}
    (OUT / 'summary.json').write_text(json.dumps(dump, ensure_ascii=False, indent=2) + '\n')
    readme = LAB / 'README.md'
    text = readme.read_text()
    result = f'В окончательном прогоне возврат на рабочую версию занял **{rollback["seconds"]:.3f} с**.\n\nДоказательства: [неисправный релиз]({broken["rollback_evidence"].rsplit("/", 1)[0]}/{relative_broken}/broken-release.log),\n[откат и успешный curl]({broken["rollback_evidence"]}/rollback.log),\n[метрика]({broken["rollback_evidence"]}/rollback.json).'
    text = text.replace('<!-- ROLLBACK_RESULT -->', result)
    readme.write_text(text)
    print('Created', OUT / 'index.html')


if __name__ == '__main__':
    main()
