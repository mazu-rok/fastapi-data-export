"""Serialize a seeded SQLite inventory and email a CSV to its operator."""
import csv
from io import StringIO

from fastapi import Request
from pydantic import BaseModel, EmailStr, TypeAdapter, ValidationError

from core import Problem, attachment
from web import create_base, client_identity


class InventoryItem(BaseModel):
    sku: str
    name: str
    quantity: int


class ExportReceipt(BaseModel):
    id: str
    email_status: str
    row_count: int


def make_csv(rows):
    output = StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=['sku', 'name', 'quantity'], lineterminator='\r\n')
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode('utf-8')


def create_app(settings=None, mailer=None):
    app = create_base('Data Export', settings, mailer, private=True)
    store = app.state.store
    with store.db() as db:
        db.execute('CREATE TABLE IF NOT EXISTS inventory(sku TEXT PRIMARY KEY, name TEXT, quantity INTEGER)')
        db.executemany('INSERT OR IGNORE INTO inventory VALUES (?,?,?)', [
            ('P-001', 'Field notebook', 18), ('P-002', 'Graphite pencil', 42),
            ('P-003', 'Canvas pencil case', 9), ('P-004', 'Desk calendar', 12),
        ])

    def items():
        with store.db() as db:
            return [dict(row) for row in db.execute('SELECT sku,name,quantity FROM inventory ORDER BY sku')]

    @app.get('/items', response_model=list[InventoryItem])
    def list_items():
        return items()

    @app.post('/exports', response_model=ExportReceipt, status_code=201)
    def export(request: Request):
        try:
            recipient = str(TypeAdapter(EmailStr).validate_python(app.state.settings.operator_email))
        except ValidationError as error:
            raise Problem('Set OPERATOR_EMAIL to the export recipient address.', 503) from error
        rows = items()
        result = store.save({'row_count': len(rows)}, {
            'to': recipient, 'subject': 'Your inventory export',
            'text': f'The attached CSV contains {len(rows)} rows from the demo inventory.',
            'attachment': attachment(make_csv(rows), 'inventory.csv', 'text/csv'),
        }, client_identity(request))
        return {**result, 'row_count': len(rows)}

    return app
