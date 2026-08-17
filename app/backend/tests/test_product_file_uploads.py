import unittest

from services.upload_service import is_supported_product_file


class ProductFileUploadTests(unittest.TestCase):
    def test_bambu_studio_product_formats_are_supported(self) -> None:
        supported = (
            "model.3mf",
            "model.gcode.3mf",
            "model.stl",
            "model.step",
            "model.stp",
            "model.svg",
            "model.amf",
            "model.zip.amf",
            "model.obj",
            "model.gltf",
            "model.glb",
            "model.fbx",
            "model.oltp",
            "model.gcode",
        )

        self.assertTrue(all(is_supported_product_file(filename) for filename in supported))

    def test_unrelated_file_formats_are_rejected(self) -> None:
        self.assertFalse(is_supported_product_file("factuur.pdf"))
        self.assertFalse(is_supported_product_file("script.exe"))
