import datetime as dt

import pytest

from app.scraper import GuestCountError, _parse_guest_count


HTML_SAMPLE = """
<html>
<body>
<div class="occupancy">Aktuelle Auslastung: <span>Anzahl Gäste 73 von 250</span></div>
</body>
</html>
"""

HTML_NO_CAPACITY = """
<html><body><div>Anzahl Gäste aktuell: 58</div></body></html>
"""

HTML_INVALID = """
<html><body><div>Keine Angaben verfügbar</div></body></html>
"""

HTML_WITH_ID = """
<table>
    <tr>
        <td id="SSD-4_visitornumber" class="stzh-datatable__cell">68</td>
        <td>Kapazität 120</td>
    </tr>
</table>
"""


def test_parse_guest_count_with_capacity():
    result = _parse_guest_count(HTML_SAMPLE)
    assert isinstance(result.count, int)
    assert result.count == 73
    assert result.capacity == 250
    assert isinstance(result.timestamp, dt.datetime)


def test_parse_guest_count_without_capacity():
    result = _parse_guest_count(HTML_NO_CAPACITY)
    assert result.count == 58
    assert result.capacity is None


def test_parse_guest_count_with_specific_id():
    result = _parse_guest_count(HTML_WITH_ID)
    assert result.count == 68
    assert result.capacity == 120


def test_parse_guest_count_failure():
    with pytest.raises(GuestCountError):
        _parse_guest_count(HTML_INVALID)
