# Copyright 2018 Capital One Services, LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

from botocore.exceptions import ClientError
from pcf.core.aws_resource import AWSResource
from pcf.core import State
from pcf.util import pcf_util

logger = logging.getLogger(__name__)

class GlacierVault(AWSResource):
    """
    This is the implementation of Amazon's Glacier service. Additional functions that are callable on this particle
    are upload_archive, initiate_job, list_jobs, delete_archive, delete_job, add_tags_to_vault, list_tags_for_vault
    """
    flavor = "glacier"

    state_lookup = {
        "missing": State.terminated,
        "active": State.running,
        "inactive": State.terminated
    }

    equivalent_states = {
        State.running: 1,
        State.stopped: 0,
        State.terminated: 0
    }

    START_PARAMS_FILTER = {
        "vaultName" # Required
    }

    def __init__(self, particle_definition):
        super(GlacierVault, self).__init__(
            particle_definition=particle_definition,
            resource_name="glacier",
        )
        self.vault_name = self.desired_state_definition["vaultName"]

    def _terminate(self):
        """
        Deletes the Glacier vault if vault is empty

        Returns:
             response of boto3 delete_vault
        """
        return self.client.delete_vault(vaultName=self.vault_name)

    def _start(self):
        """
        Creates the Glacier vault

        Returns:
             response of boto3 create_vault
        """
        create_definition = pcf_util.param_filter(self.get_desired_state_definition(), self.START_PARAMS_FILTER)
        response = self.client.create_vault(**create_definition)

        if self.custom_config.get("Tags"):
            tags = self.custom_config.get("Tags")

            self.client.add_tags_to_vault(
                vaultName=self.vault_name,
                Tags=tags
            )
        return response


    def _stop(self):
        """
        Glacier does not have a stopped state so it calls terminate.
        """
        return self.terminate()

    def get_status(self):
        """
        Determines if the vault exists

        Returns:
             status (dict)
        """

        try:
            vault_object = self.client.describe_vault(
                vaultName=self.vault_name,
                accountId="-"
            )
        except ClientError as e:
            logger.info("{}. State is missing".format(e))
            return {"status":"missing"}
        return {"status":"active"}

    def sync_state(self):
        """
        Uses get_status() to determine whether the vault exists or not and sets the current state definition

        Returns:
            void
        """

        full_status = self.get_status()

        if full_status:
            status = full_status.get("status", "missing").lower()
            self.state = self.state_lookup.get(status)

            # set current state definition
            self.current_state_definition = self.desired_state_definition

    def _update(self):
        """
        Not Implemented
        """
        pass

    def is_state_equivalent(self, state1, state2):
        """
        Determines if states are equivalent. Uses equivalent_states defined in the Glacier class.

        Args:
            state1 (State):
            state1 (State):

        Returns:
            bool
        """
        return self.equivalent_states.get(state1) == self.equivalent_states.get(state2)
