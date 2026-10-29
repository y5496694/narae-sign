import importlib.util
from pathlib import Path
import tempfile
import unittest
from PIL import Image

spec=importlib.util.spec_from_file_location('signature',Path(__file__).parents[1]/'signature.py')
signature=importlib.util.module_from_spec(spec)
spec.loader.exec_module(signature)


class SignatureTests(unittest.TestCase):
    def test_empty_rejected(self):
        for strokes in ([],[[]]):
            with self.assertRaises(ValueError): signature.render_signature(strokes)

    def test_ink_only_cropped_and_antialiased(self):
        image=signature.render_signature([[(100,100),(180,150),(240,90)]])
        self.assertEqual(image.mode,'RGBA')
        self.assertLess(image.width,200)
        self.assertLess(image.height,110)
        alpha=image.getchannel('A')
        self.assertEqual(alpha.getextrema(),(0,255))
        self.assertTrue(any(0<a<255 for a in alpha.getdata()))
        self.assertEqual(image.getpixel((0,0))[3],0)
        self.assertTrue(all(r==g==b==0 for r,g,b,a in image.getdata() if a))

    def test_point_and_edge_strokes(self):
        for strokes in ([[(0,0)]],[[(899,309),(850,290)]],[[(10,10)],[(30,30),(70,30)]]):
            image=signature.render_signature(strokes)
            self.assertIsNotNone(image.getchannel('A').getbbox())
            self.assertGreater(image.width,0)

    def test_png_and_confirmation_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'signature.png'
            receipt=Path(directory)/'saved.json'
            image=signature.render_signature([[(20,20),(80,45)]])
            result=signature.save_signature(image,target,receipt)
            self.assertTrue(result['saved'] and result['transparent'])
            self.assertEqual(result['source'],'user-drawn-confirmed')
            with Image.open(target) as saved:
                self.assertEqual(saved.mode,'RGBA')
                self.assertEqual(saved.getchannel('A').getextrema(),(0,255))
            self.assertTrue(receipt.exists())

    def test_only_png_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                signature.save_signature(signature.render_signature([[(1,1)]]),Path(directory)/'signature.jpg')


if __name__=='__main__': unittest.main()
