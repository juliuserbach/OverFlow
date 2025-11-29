from app.scraper import _extract_pools_from_html, _strip_tags


HTML_POOLS = """
<stzh-datatable id="baederinfossummary" tableLayout="auto" rows="[[{&#34;id&#34;:&#34;&#34;,&#34;value&#34;:&#34;&lt;a href=\\\"/foo\\\">Pool A&lt;/a>&#34;,&#34;isHeader&#34;:false},{&#34;id&#34;:&#34;SSD-1&#34;,&#34;value&#34;:&#34;-&#34;,&#34;isHeader&#34;:false},{&#34;id&#34;:&#34;SSD-1_visitornumber&#34;,&#34;value&#34;:&#34;-&#34;,&#34;isHeader&#34;:false}],[{&#34;id&#34;:&#34;&#34;,&#34;value&#34;:&#34;Pool B&#34;,&#34;isHeader&#34;:false},{&#34;id&#34;:&#34;SSD-2&#34;,&#34;value&#34;:&#34;-&#34;,&#34;isHeader&#34;:false},{&#34;id&#34;:&#34;SSD-2_visitornumber&#34;,&#34;value&#34;:&#34;-&#34;,&#34;isHeader&#34;:false}]]" columns="[]">
</stzh-datatable>
"""


def test_extract_pools():
    pools = _extract_pools_from_html(HTML_POOLS)
    assert pools == {"SSD-1": "Pool A", "SSD-2": "Pool B"}


def test_strip_tags():
    assert _strip_tags("<a>Test</a>") == "Test"
