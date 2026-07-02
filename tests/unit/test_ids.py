from app.shared.ids import new_id, timestamp_id

def test_ids_have_prefix():
    assert new_id('rec').startswith('rec_')
    assert timestamp_id('batch').startswith('batch_')
