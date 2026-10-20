"""game/system/rng.py - 난수를 용도별 흐름으로 나눈다.

한 흐름에서 굴림이 하나 늘어도 다른 흐름은 밀리지 않아야 한다(골든이 한꺼번에 바뀌는 것을 줄인다).
"""

from game.system import rng


def test_시드가_같으면_모든_흐름이_같은_값을_낸다():
    rng.시드(5)
    처음 = [흐름.random() for 흐름 in rng.흐름들.values()]
    rng.시드(5)
    assert [흐름.random() for 흐름 in rng.흐름들.values()] == 처음


def test_흐름마다_다른_값을_낸다():
    rng.시드(5)
    값들 = [흐름.random() for 흐름 in rng.흐름들.values()]
    assert len(set(값들)) == len(값들)


def test_한_흐름을_더_굴려도_다른_흐름은_밀리지_않는다():
    rng.시드(1)
    rng.주사위.randint(1, 20)
    기준 = rng.대상.random()
    rng.시드(1)
    for _ in range(10):
        rng.주사위.randint(1, 20)  # 주사위를 열 번 더 굴려도
    assert rng.대상.random() == 기준  # 대상 고르기는 그대로


def test_시드는_전역_random도_고정한다():
    """테스트의 플레이어 정책(tests/scenario.py)은 전역 random을 쓴다 - 시나리오 시드를 따라야 한다."""
    import random

    rng.시드(3)
    처음 = random.random()
    rng.시드(3)
    assert random.random() == 처음


def test_흐름은_용도별로_다섯이다():
    assert list(rng.흐름들) == ["주사위", "확률", "대상", "던전", "보상"]
    assert rng.흐름들["주사위"] is rng.주사위


def test_상태를_저장하고_되돌리면_모든_흐름이_같은_자리로_돌아간다():
    """화면 스모크는 중간 단계의 굴림이 뒤 단계를 바꾸지 않게 난수 상태를 저장하고 되돌린다."""
    import random

    rng.시드(4)
    저장 = rng.상태()
    처음 = [흐름.random() for 흐름 in rng.흐름들.values()] + [random.random()]
    rng.상태_복원(저장)
    assert [흐름.random() for 흐름 in rng.흐름들.values()] + [random.random()] == 처음
