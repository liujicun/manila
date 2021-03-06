# Copyright (c) 2013 OpenStack Foundation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mock

from manila.scheduler.filters import base
from manila import test


class TestBaseFilter(test.TestCase):

    def setUp(self):
        super(TestBaseFilter, self).setUp()
        self.filter = base.BaseFilter()

    def test_filter_one_is_called(self):

        filters = [1, 2, 3, 4]
        filter_properties = {'x': 'y'}

        side_effect = lambda value, props: value in [2, 3]
        self.mock_object(self.filter,
                         '_filter_one',
                         mock.Mock(side_effect=side_effect))

        result = list(self.filter.filter_all(filters, filter_properties))

        self.assertEqual([2, 3], result)


class FakeExtension(object):

    def __init__(self, plugin):
        self.plugin = plugin


class BaseFakeFilter(base.BaseFilter):
    pass


class FakeFilter1(BaseFakeFilter):
    """Derives from BaseFakeFilter and has a fake entry point defined.

    Entry point is returned by fake ExtensionManager.
    Should be included in the output of all_classes.
    """


class FakeFilter2(BaseFakeFilter):
    """Derives from BaseFakeFilter but has no entry point.

    Should be not included in all_classes.
    """


class FakeFilter3(base.BaseFilter):
    """Does not derive from BaseFakeFilter.

    Should not be included.
    """


class FakeFilter4(BaseFakeFilter):
    """Derives from BaseFakeFilter and has an entry point.

    Should be included.
    """


class FakeFilter5(BaseFakeFilter):
    """Derives from BaseFakeFilter but has no entry point.

    Should not be included.
    """
    run_filter_once_per_request = True


class FakeExtensionManager(list):

    def __init__(self, namespace):
        classes = [FakeFilter1, FakeFilter3, FakeFilter4]
        exts = map(FakeExtension, classes)
        super(FakeExtensionManager, self).__init__(exts)
        self.namespace = namespace


class TestBaseFilterHandler(test.TestCase):

    def setUp(self):
        super(TestBaseFilterHandler, self).setUp()
        self.mock_object(base.base_handler.extension,
                         'ExtensionManager',
                         FakeExtensionManager)
        self.handler = base.BaseFilterHandler(BaseFakeFilter, 'fake_filters')

    def test_get_all_classes(self):
        # In order for a FakeFilter to be returned by get_all_classes, it has
        # to comply with these rules:
        # * It must be derived from BaseFakeFilter
        #   AND
        # * It must have a python entrypoint assigned (returned by
        #   FakeExtensionManager)
        expected = [FakeFilter1, FakeFilter4]
        result = self.handler.get_all_classes()
        self.assertEqual(expected, result)

    def _get_filtered_objects(self, filter_classes, index=0):
        filter_objs_initial = [1, 2, 3, 4]
        filter_properties = {'x': 'y'}
        return self.handler.get_filtered_objects(filter_classes,
                                                 filter_objs_initial,
                                                 filter_properties,
                                                 index)

    @mock.patch.object(FakeFilter4, 'filter_all')
    @mock.patch.object(FakeFilter3, 'filter_all', return_value=None)
    def test_get_filtered_objects_return_none(self, fake3_filter_all,
                                              fake4_filter_all):
        filter_classes = [FakeFilter1, FakeFilter2, FakeFilter3, FakeFilter4]
        result = self._get_filtered_objects(filter_classes)
        self.assertIsNone(result)
        self.assertFalse(fake4_filter_all.called)

    def test_get_filtered_objects(self):
        filter_objs_expected = [1, 2, 3, 4]
        filter_classes = [FakeFilter1, FakeFilter2, FakeFilter3, FakeFilter4]
        result = self._get_filtered_objects(filter_classes)
        self.assertEqual(filter_objs_expected, result)

    def test_get_filtered_objects_with_filter_run_once(self):
        filter_objs_expected = [1, 2, 3, 4]
        filter_classes = [FakeFilter5]

        with mock.patch.object(FakeFilter5, 'filter_all',
                               return_value=filter_objs_expected
                               ) as fake5_filter_all:
            result = self._get_filtered_objects(filter_classes)
            self.assertEqual(filter_objs_expected, result)
            self.assertEqual(1, fake5_filter_all.call_count)

            result = self._get_filtered_objects(filter_classes, index=1)
            self.assertEqual(filter_objs_expected, result)
            self.assertEqual(1, fake5_filter_all.call_count)

            result = self._get_filtered_objects(filter_classes, index=2)
            self.assertEqual(filter_objs_expected, result)
            self.assertEqual(1, fake5_filter_all.call_count)
