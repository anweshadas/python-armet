# -*- coding: utf-8 -*-
import hashlib
# from armet import http
from armet.utils import test


class ResponseTestCase(test.TestCase):

    def test_content_md5(self):
        import ipdb
        ipdb.set_trace()
        # Check some random endpoint
        response = self.client.get('/choice/')
        # Assert we got a Content-MD5 header
        self.assertTrue(response.has_header('Content-MD5'))
        # Make an MD5 of the body.
        md5_body = hashlib.md5(response.content).hexdigest()
        # Assert the MD5 is correct.
        self.assertEqual(response['Content-MD5'], md5_body)
        # This fails with 404 for now (no template)
        # # Check a blank content
        # # should be 'd41d8cd98f00b204e9800998ecf8427e'
        # endpoint = '{}choice/thisendpointisbunk'
        # response = self.client.get(endpoint)
        # # Assert we got a Content-MD5 header
        # self.assertTrue(response.has_header('Content-MD5'))
        # # Make an MD5 of the body.
        # md5_body = hashlib.md5(response.content).hexdigest()
        # # Assert the MD5 is correct.
        # self.assertEqual(response['Content-MD5'], md5_body)
