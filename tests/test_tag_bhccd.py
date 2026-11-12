import unittest
from src.tag_bhccd import one_cream, is_eligible, unique_id

def order(products=None, tracking="", tags=None):
    return {
        "status_id": 7,
        "shipping": {"delivery_service_id": 4, "tracking_code": tracking},
        "products": [{"sku": "BHCCD", "quantity": 1}] if products is None else products,
        "tags": [] if tags is None else tags,
    }

class CreamTests(unittest.TestCase):
    def test_exact_match(self):
        self.assertTrue(one_cream(order()))
        self.assertTrue(is_eligible(order(), 7, 4, 12))
    def test_no_other_items(self):
        self.assertFalse(one_cream(order([{"sku":"BHCCD","quantity":1},{"sku":"LIP","quantity":1}])))
    def test_quantity_and_sku(self):
        self.assertFalse(one_cream(order([{"sku":"BHCCD","quantity":2}])))
        self.assertFalse(one_cream(order([{"sku":"BHCCD2","quantity":1}])))
    def test_nested_offer(self):
        self.assertTrue(one_cream(order([{"offer":{"sku":"BHCCD"},"quantity":1}])))
    def test_status_and_delivery(self):
        self.assertFalse(is_eligible(order(), 8, 4, 12))
        self.assertFalse(is_eligible(order(), 7, 5, 12))
    def test_tracking_tag_and_missing_fields(self):
        self.assertFalse(is_eligible(order(tracking="2045000"), 7, 4, 12))
        self.assertFalse(is_eligible(order(tags=[{"id":12}]), 7, 4, 12))
        bad = order()
        del bad["shipping"]["tracking_code"]
        self.assertFalse(is_eligible(bad, 7, 4, 12))
    def test_fail_closed(self):
        self.assertFalse(one_cream({"products":[]}))
        self.assertFalse(is_eligible({"status_id":7},7,4,12))
    def test_unique_ids(self):
        self.assertEqual(unique_id([{"id":9,"name":"ПОВНА ОПЛАТА"}],"повна оплата"),9)
        with self.assertRaises(ValueError):
            unique_id([], "BHCCD_1PC")
        with self.assertRaises(ValueError):
            unique_id([{"id":1,"name":"x"},{"id":2,"name":"x"}],"x")

if __name__ == "__main__":
    unittest.main()
