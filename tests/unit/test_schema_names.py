from app.shared.schema_names import edge_name, query_name, table_name, vertex_name

def test_schema_name_prefix():
    assert vertex_name('Advisor') == 'phx_dm_advisor'
    assert edge_name('HAS_ACCOUNT') == 'phx_dm_has_account'
    assert table_name('Feature_Registry') == 'phx_dm_feature_registry'
    assert query_name('getAdvisor') == 'phx_dm_getAdvisor'
