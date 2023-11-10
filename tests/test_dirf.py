
from jocassid_commons.dirf import dirf


class Thingy:

    @staticmethod
    def foo_bar(self):
        pass

    @staticmethod
    def foo_Bar(self):
        pass


class TestDirf:

    def test_simple_contains(self):
        expected = ['lstrip', 'rstrip', 'strip']
        assert expected == dirf('a', 'strip')

    def test_case_sensitive_contains(self):
        expected = ['foo_bar']
        assert expected == dirf(Thingy, 'bar', ignore_case=False)

    def test_startswith(self):
        expected = ['title', 'translate']
        assert expected == dirf('a', 't', starts_with=True)

    def test_no_obj(self):
        # declare some variable so there's more than 'self' in the current
        # frame's local variables
        elf = 'elf'
        dwarf = 'dwarf'

        dir_list = dir()
        dir_list.remove('dwarf')

        assert dir_list == dirf('elf')
        len([elf, dwarf])

