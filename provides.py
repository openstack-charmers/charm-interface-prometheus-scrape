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

from charms.reactive import (
    clear_flag,  # noqa: H301
    Endpoint,
    set_flag,
    when,
    when_not,
)
from charmhelpers.core import hookenv

import charmhelpers.contrib.network.ip as ch_net_ip
import json


class PrometheusScrapeProvides(Endpoint):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ingress_address = ch_net_ip.get_relation_ip(self.endpoint_name)

    @when('endpoint.{endpoint_name}.joined')
    def joined(self):
        set_flag(self.expand_name('{endpoint_name}.connected'))

    @when('endpoint.{endpoint_name}.changed')
    def changed(self):
        set_flag(self.expand_name('{endpoint_name}.available'))

    @when_not('endpoint.{endpoint_name}.joined')
    def departed(self):
        flags = (
            self.expand_name('{endpoint_name}.connected'),
            self.expand_name('{endpoint_name}.available'),
        )
        for flag in flags:
            clear_flag(flag)

    def expose_job(self, job_name='', metrics_path="/metrics",
                   static_configs={}):
        """Expose a single scrape job with possible customizations.

        Follows the format described by Prometheus for scrape config and which
        the receiving side expects to find in the unit and app relation data.

        https://prometheus.io/docs/prometheus/latest/configuration/configuration/#scrape_config
        """
        if not static_configs:
            static_configs = [{"targets": ["*:80"]}]

        for rel in self.relations:
            rel.to_publish_raw['prometheus_scrape_unit_name'] = (
                hookenv.local_unit().replace('/', '-'))
            rel.to_publish_raw[
                'prometheus_scrape_unit_address'] = self.ingress_address

            if hookenv.is_leader():
                rel.to_publish_app['scrape_jobs'] = [{
                    # Job names are arbitrary in Prometheus at the time of
                    # writing, see commit
                    # 1aa8898b6649527a16fbdeffea19894ea9092431, PR 1996
                    # in the Prometheus repo.
                    'job_name': job_name,
                    'metrics_path': metrics_path,
                    'static_configs': static_configs,
                }]
                rel.to_publish_app['scrape_metadata'] = {
                    'model': hookenv.model_name(),
                    'model_uuid': hookenv.model_uuid(),
                    'application': hookenv.application_name(),
                }

        set_flag(self.expand_name('{endpoint_name}.exposed' + f'.{job_name}'))

    def clear_job(self, job_name):
        """Clear a named job state on the relation if present."""
        for rel in self.relations:
            rel.to_publish.pop('prometheus_scrape_unit_name', None)
            rel.to_publish.pop('prometheus_scrape_unit_address', None)

            if hookenv.is_leader():
                jobs = json.loads(rel.to_publish_app['scrape_jobs'])
                jobs.pop(job_name, None)
                rel.to_publish_app['scrape_jobs'] = jobs

            clear_flag(self.expand_name(
                '{endpoint_name}.exposed' + f'.{job_name}'))
