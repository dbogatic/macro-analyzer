from engine.triggers import evaluate_triggers


def test_triggers_created():
    triggers = evaluate_triggers({
        "unemployment": 4.6,
        "core_pce": 3.1,
        "hy_spread": 5.2,
        "2y": 4.2,
        "10y": 3.8,
    })
    assert len(triggers) == 4
    assert any(t.fired for t in triggers)
