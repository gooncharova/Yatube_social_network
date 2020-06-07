import datetime as dt


def year(request):
    year = dt.datetime.now().year
    return {"year": year}
