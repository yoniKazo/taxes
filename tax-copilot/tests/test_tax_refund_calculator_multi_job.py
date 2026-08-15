import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pytest

from tax_refund_calculator import (
    NI_CEILING,
    InvalidInputError,
    JobInput,
    calc_ni_and_health,
    calculate,
    calculate_multi_job,
)


def test_two_jobs_matches_single_calculate_on_combined_gross():
    jobs = [JobInput(8000), JobInput(6000)]
    multi = calculate_multi_job(jobs, "male")
    single = calculate(14000, "male")

    assert multi.combined_gross == 14000
    assert multi.job_count == 2
    assert multi.result == single


def test_two_jobs_matches_existing_13000_male_spec_row():
    jobs = [JobInput(7000), JobInput(6000)]
    multi = calculate_multi_job(jobs, "male")

    assert multi.result.tax_before_credit == 1716.00
    assert multi.result.tax_after_credit == 1171.50
    assert multi.result.national_insurance == 450.90
    assert multi.result.health_tax == 522.66
    assert multi.result.net == 10854.94


def test_single_job_matches_calculate_directly():
    jobs = [JobInput(20000)]
    multi = calculate_multi_job(jobs, "female")
    single = calculate(20000, "female")

    assert multi.combined_gross == 20000
    assert multi.job_count == 1
    assert multi.result == single


def test_empty_jobs_list_raises():
    with pytest.raises(InvalidInputError):
        calculate_multi_job([], "male")


def test_job_with_non_positive_gross_salary_raises():
    with pytest.raises(InvalidInputError):
        calculate_multi_job([JobInput(5000), JobInput(0)], "male")


def test_ni_ceiling_applies_once_to_combined_income_not_per_job():
    jobs = [JobInput(40000), JobInput(40000)]
    combined_gross = 80000
    assert combined_gross > NI_CEILING

    multi = calculate_multi_job(jobs, "male")
    expected_ni, expected_health = calc_ni_and_health(combined_gross)

    assert multi.combined_gross == combined_gross
    assert multi.result.national_insurance == expected_ni
    assert multi.result.health_tax == expected_health
