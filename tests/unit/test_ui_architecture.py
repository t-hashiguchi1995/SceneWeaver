from __future__ import annotations

import importlib.util
import stat
import zipfile
from pathlib import Path

import pytest

from creator_studio.application.prompt.assembly import build_default_prompt
from creator_studio.domain.prompt.assembly import PromptAssemblyProfile, PromptComponent


def importer():
    import sys
    spec = importlib.util.spec_from_file_location('architecture_importer', Path(__file__).parents[2] / 'scripts/import_legacy_prompts.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('name', ['../escape.yaml', '/absolute.yaml', 'C:/escape.yaml', 'prompts/../../escape.yaml', '..\\escape.yaml'])
def test_zip_rejects_traversal(tmp_path, name):
    archive = tmp_path / 'prompts.zip'
    with zipfile.ZipFile(archive, 'w') as zf:
        zf.writestr(name, 'key: value')
    with pytest.raises(ValueError, match='unsafe'):
        list(importer().iter_source_files(archive))
    assert not (tmp_path / 'escape.yaml').exists()


def test_zip_rejects_symlink_and_size(tmp_path):
    module = importer()
    archive = tmp_path / 'prompts.zip'
    link = zipfile.ZipInfo('link.yaml')
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(archive, 'w') as zf:
        zf.writestr(link, '../target')
    with pytest.raises(ValueError, match='unsafe'):
        list(module.iter_source_files(archive))
    module.MAX_ZIP_MEMBER_BYTES = 4
    with zipfile.ZipFile(archive, 'w') as zf:
        zf.writestr('safe.yaml', 'hello: world')
    with pytest.raises(ValueError, match='size limit'):
        list(module.iter_source_files(archive))


def test_zip_temporary_directory_cleanup(tmp_path):
    archive = tmp_path / 'prompts.zip'
    with zipfile.ZipFile(archive, 'w') as zf:
        zf.writestr('prompts/sfw_test.yml', 'key: value')
    iterator = importer().iter_source_files(archive)
    name, path = next(iterator)
    assert name == 'sfw_test.yml'
    assert path.read_text() == 'key: value'
    iterator.close()
    assert not path.exists()


def test_assembly_conflicts_policy_and_determinism():
    components = [
        PromptComponent('lighting:default', 'lighting', 'indoor', precedence=0),
        PromptComponent('lighting:shot', 'lighting', 'sunset', precedence=2),
        PromptComponent('mouth:closed', 'expression', 'closed mouth', subkind='mouth', priority=1),
        PromptComponent('mouth:open', 'expression', 'open mouth', subkind='mouth'),
        PromptComponent('emotion:shy', 'expression', 'shy', subkind='emotion'),
        PromptComponent('style:test', 'style', 'anime, <lora:test:0.8>'),
        PromptComponent('adult:test', 'background', 'excluded', content_rating='adult', precedence=9),
    ]
    profile = PromptAssemblyProfile()
    result = build_default_prompt(components, profile)
    for offset in range(100):
        shuffled = components[offset % len(components):] + components[:offset % len(components)]
        assert build_default_prompt(shuffled, profile) == result
    assert 'sunset' in result.positive and 'indoor' not in result.positive
    assert 'closed mouth' in result.positive and 'open mouth' not in result.positive
    assert 'shy' in result.positive and 'excluded' not in result.positive
    assert '<lora:' not in result.positive
    assert result.model_modifiers == [{'kind': 'lora', 'model': 'test', 'strength': 0.8}]
    assert result.warnings
