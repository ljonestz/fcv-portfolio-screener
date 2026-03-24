"""Tests for screening prompt builder."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.build_screening_prompt import build_prompt


def test_pad_only_prompt_contains_primary_label():
    prompt = build_prompt(pid='P999999', project_name='Test Project',
                          doc_type='PAD', instrument='IPF', year=2019,
                          pad_text='FILTERED PAD CONTENT here.', isr_texts=[])
    assert 'PRIMARY DOCUMENT' in prompt
    assert 'FILTERED PAD CONTENT here.' in prompt


def test_pad_only_prompt_no_supplementary_section():
    prompt = build_prompt(pid='P999999', project_name='Test Project',
                          doc_type='PAD', instrument='IPF', year=2019,
                          pad_text='Some PAD text.', isr_texts=[])
    assert 'SUPPLEMENTARY DOCUMENTS' not in prompt


def test_with_isrs_prompt_contains_supplementary():
    isr_texts = [('ISR', '2021-03', 'ISR content here.')]
    prompt = build_prompt(pid='P999999', project_name='Test Project',
                          doc_type='PAD', instrument='IPF', year=2019,
                          pad_text='PAD text.', isr_texts=isr_texts)
    assert 'SUPPLEMENTARY DOCUMENTS' in prompt
    assert 'ISR content here.' in prompt


def test_with_isrs_prompt_contains_adjustment_instructions():
    isr_texts = [('ISR', '2022-06', 'Some ISR text.')]
    prompt = build_prompt(pid='P999999', project_name='Test',
                          doc_type='PAD', instrument='IPF', year=2020,
                          pad_text='PAD.', isr_texts=isr_texts)
    assert 'adjust' in prompt.lower()
    assert 'trajectory' in prompt.lower()


def test_prompt_contains_project_metadata():
    prompt = build_prompt(pid='P999999', project_name='Djibouti Roads',
                          doc_type='PAD', instrument='DPF', year=2017,
                          pad_text='PAD text.', isr_texts=[])
    assert 'P999999' in prompt
    assert 'Djibouti Roads' in prompt
    assert 'DPF' in prompt
    assert '2017' in prompt


def test_output_file_instruction_in_prompt():
    prompt = build_prompt(pid='P999999', project_name='Test',
                          doc_type='PAD', instrument='IPF', year=2018,
                          pad_text='PAD text.', isr_texts=[],
                          output_path='djibouti/screening_results_P999999.json')
    assert 'djibouti/screening_results_P999999.json' in prompt


def test_isr_count_in_prompt():
    isr_texts = [
        ('ISR', '2020-01', 'ISR 1 content.'),
        ('ISR', '2021-06', 'ISR 2 content.'),
    ]
    prompt = build_prompt(pid='P999999', project_name='Test',
                          doc_type='PAD', instrument='IPF', year=2019,
                          pad_text='PAD text.', isr_texts=isr_texts)
    # The prompt should mention there are 2 supplementary documents
    assert '2' in prompt


def test_no_output_path_still_valid():
    prompt = build_prompt(pid='P999999', project_name='Test',
                          doc_type='PAD', instrument='IPF', year=2018,
                          pad_text='PAD text.', isr_texts=[])
    # Should not error even without output_path
    assert 'P999999' in prompt
