import datetime as dt


def year(request):
    """Добавляет переменную с текущим годом."""
    today = dt.datetime.today().year
    return {
        'year': today,
    }
