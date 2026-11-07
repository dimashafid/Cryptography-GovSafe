from io import BytesIO
from pathlib import Path
from PIL import Image
from database import db_manager
from services import catalog_service, message_service, purchase_service
from blockchain.blockchain import create_genesis_block, get_all_blocks, validate_chain


def test_end_to_end_crypto_workflow(tmp_path, monkeypatch):
    db_path = tmp_path / "undergrid.db"
    storage = tmp_path / "encrypted-products"
    monkeypatch.setattr(catalog_service, "STORAGE_PATH", storage)
    db_manager.init_db(db_path)
    create_genesis_block(db_path)

    image = Image.new("RGB", (200, 200), (20, 80, 40))
    image_path = tmp_path / "product.png"
    image.save(image_path, format="PNG")
    csv_path = tmp_path / "catalog.csv"
    csv_path.write_text(
        "sku,name,category,description,specifications,price,seller_contact,image_path,secret_note,status\n"
        f"UG-TEST,Test Item,Demo,Description,Specs,Rp 10.000 (simulasi),seller@example.invalid,{image_path},Hidden note,available\n",
        encoding="utf-8",
    )

    assert catalog_service.import_catalog_csv(csv_path, db_path) == 1
    products = catalog_service.get_catalog(db_path)
    detail = catalog_service.get_product_detail(products[0]["id"], db_path)
    assert detail["image_bytes"].startswith(b"\x89PNG")
    assert detail["secret_metadata"]["secret_note"] == "Hidden note"

    buyer_id = db_manager.add_buyer("buyer-test", "$argon2id$test", db_path)
    message_service.send_message(buyer_id, "Confidential demo message", db_path=db_path)
    stored = message_service.get_buyer_messages(buyer_id, db_path)[0]
    assert message_service.decrypt_for_admin(stored["encrypted_message"]) == "Confidential demo message"

    purchase_service.create_purchase_intent(buyer_id, products[0]["id"], db_path)
    purchase_service.request_information(buyer_id, products[0]["id"], db_path)
    blocks = get_all_blocks(db_path)
    assert len(blocks) == 3
    assert validate_chain(blocks)
