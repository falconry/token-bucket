# Copyright 2016 by Rackspace Hosting, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .storage_base import StorageBase


class MemoryStorage(StorageBase):
    """In-memory token bucket storage engine.

    This storage engine is suitable for multi-threaded applications. For
    performance reasons, race conditions are mitigated but not completely
    eliminated. The remaining effects have the result of reducing the
    effective bucket capacity by a negligible amount. In practice this
    won't be noticeable for the vast majority of applications, but in
    the case that it is, the situation can be remedied by simply
    increasing the bucket capacity by a few tokens.
    """
    bucket_provider_cls = dict
