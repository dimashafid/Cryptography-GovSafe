from database import db_manager

def test_database_crud_and_sensitive_product_encryption(tmp_path):
    db = tmp_path / "test.db"
    db_manager.init_db(db)
    buyer_id = db_manager.add_buyer("buyer1", "$argon2id$dummy", db)
    assert db_manager.get_buyer_by_id(buyer_id, db)["username"] == "buyer1"
    product_id = db_manager.add_product({
        "sku":"UG-001", "category":"Accessories", "title":"Secure Notebook",
        "description":"Fictional product", "specifications":"A5",
        "seller_contact":"seller@example.invalid", "secret_metadata":{"secret":"x"},
        "price_display":"Rp 100.000 (simulasi)", "image_path":"storage/UG-001.enc"
    }, db)
    product = db_manager.get_product(product_id, db)
    assert product["title"] == "Secure Notebook"
    assert product["secret_metadata"] == {"secret":"x"}
    with db_manager.get_connection(db) as conn:
        raw = conn.execute("SELECT encrypted_title FROM products WHERE id=?", (product_id,)).fetchone()[0]
    assert b"Secure Notebook" not in raw
