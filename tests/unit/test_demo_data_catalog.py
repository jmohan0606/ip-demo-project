from app.services.demo_data_catalog_service import DemoDataCatalogService


def test_demo_data_manifest():
    manifest = DemoDataCatalogService().manifest()
    assert manifest["scale"]["advisors"] >= 150
    assert manifest["scale"]["transactions"] >= 100000


def test_demo_data_files():
    files = DemoDataCatalogService().list_csv_files()
    names = {f["file_name"] for f in files}
    assert "phx_dm_advisor.csv" in names
    assert "phx_dm_transaction.csv" in names
