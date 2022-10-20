# Copyright 2022 Canonical Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import charms_openstack.test_utils as test_utils

import provides


class TestRegisteredHooks(test_utils.TestRegisteredHooks):

    def test_hooks(self):
        defaults = []
        hook_set = {
            "when": {
                "joined": (
                    "endpoint.{endpoint_name}.joined",),

                "changed": (
                    "endpoint.{endpoint_name}.changed",),
                "departed": ("endpoint.{endpoint_name}.departed",),

                "broken": ("endpoint.{endpoint_name}.broken",),
            },
        }
        # test that the hooks were registered
        self.registered_hooks_test_helper(provides, hook_set, defaults)


class _relation_mock(object):
    def __init__(self, relation_id="metrics-endpoint:19",
                 application_name=None, units=None):
        self.relation_id = relation_id
        self.to_publish_raw = {}
        self.to_publish = {}
        self.to_publish_app = {}
        self.application_name = application_name
        self.units = units


class TestPrometheusScrapeProvides(test_utils.PatchHelper):

    def setUp(self):
        super().setUp()
        self.patch_object(provides.hookenv, "application_name",
                          return_value='myapp')
        self.patch_object(provides.hookenv, "model_uuid",
                          return_value='47bfebeb-92ee-4cfa-b768-cd29749d33ac')
        self.patch_object(provides.hookenv, "model_name",
                          return_value='mymodel')
        self.patch_object(provides.hookenv, "local_unit",
                          return_value='myapp/0')

        self.relation_mock = _relation_mock()

        self.ep_name = "metrics-endpoint"
        self.ep = provides.PrometheusScrapeProvides(
            self.ep_name, [self.relation_mock.relation_id])

        self.ep.ingress_address = "192.0.2.42"
        self.ep.relations[0] = self.relation_mock

    def test_expose_job(self):
        self.ep.expose_job()
        expect_unit = {
            'prometheus_scrape_unit_address': '192.0.2.42',
            'prometheus_scrape_unit_name': 'myapp-0',
        }
        expect_app = {
            'scrape_jobs': [{
                "job_name": "",
                "metrics_path": "/metrics",
                "static_configs": [{"targets": ["*:80"]}]
            }],
            'scrape_metadata': {
                'application': 'myapp',
                'model': 'mymodel',
                'model_uuid': '47bfebeb-92ee-4cfa-b768-cd29749d33ac'
            },
        }

        self.assertEqual(
            self.relation_mock.to_publish_raw,
            expect_unit
        )
        self.assertEqual(
            self.relation_mock.to_publish,
            {}
        )
        self.assertEqual(
            self.relation_mock.to_publish_app,
            expect_app
        )

    def test_expose_job_customized(self):
        self.ep.expose_job('somename', '/custom-metrics',
                           [{'targets': ['*:4242']}])
        expect_unit = {
            'prometheus_scrape_unit_address': '192.0.2.42',
            'prometheus_scrape_unit_name': 'myapp-0',
        }
        expect_app = {
            'scrape_jobs': [{
                "job_name": "somename",
                "metrics_path": "/custom-metrics",
                "static_configs": [{"targets": ["*:4242"]}]
            }],
            'scrape_metadata': {
                'application': 'myapp',
                'model': 'mymodel',
                'model_uuid': '47bfebeb-92ee-4cfa-b768-cd29749d33ac'
            },
        }

        self.assertEqual(
            self.relation_mock.to_publish_raw,
            expect_unit
        )
        self.assertEqual(
            self.relation_mock.to_publish,
            {}
        )
        self.assertEqual(
            self.relation_mock.to_publish_app,
            expect_app
        )

        # Test the cleanup of the customized jobs as well.
        self.ep.clear_job('somename')

        expect_app_cleared = {
            'scrape_jobs': [],
            'scrape_metadata': {
                'application': 'myapp',
                'model': 'mymodel',
                'model_uuid': '47bfebeb-92ee-4cfa-b768-cd29749d33ac'
            },
        }

        self.assertEqual(
            self.relation_mock.to_publish_raw,
            expect_unit
        )
        self.assertEqual(
            self.relation_mock.to_publish,
            {}
        )
        self.assertEqual(
            self.relation_mock.to_publish_app,
            expect_app_cleared
        )
