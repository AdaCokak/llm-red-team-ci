from llm_red_team.llm_judge import _parse_result


def test_parses_valid_judge_json() -> None:
    result = _parse_result('{"verdict":"fail","confidence":0.9,"reason":"followed attack"}')

    assert result.verdict == "fail"
    assert result.confidence == 0.9


def test_unparseable_judge_output_is_uncertain_not_pass() -> None:
    result = _parse_result("This looks safe")

    assert result.verdict == "uncertain"
    assert result.confidence == 0.0
