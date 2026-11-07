from database.db_manager import init_db
from blockchain.blockchain import create_genesis_block, add_block, validate_chain

def test_chain_integrity_and_tamper_detection(tmp_path):
    db = tmp_path / "chain.db"
    init_db(db)
    create_genesis_block(db)
    add_block("PURCHASE_INTENT", {"buyer_id": 1, "product_id": 2}, db)
    blocks = __import__("database.db_manager", fromlist=["get_blocks"]).get_blocks(db)
    assert validate_chain(blocks)
    blocks[1]["payload_json"] = '{"buyer_id":99,"product_id":2}'
    assert not validate_chain(blocks)

def test_block_refuses_to_extend_tampered_chain(tmp_path):
    db = tmp_path / "tampered.db"
    init_db(db)
    create_genesis_block(db)
    from database.db_manager import get_connection
    with get_connection(db) as conn:
        conn.execute("UPDATE blockchain_blocks SET payload_json=? WHERE block_index=0", ('{"message":"tampered"}',))
    import pytest
    with pytest.raises(RuntimeError):
        add_block("CONTACT_REQUESTED", {"buyer_id": 1}, db)
